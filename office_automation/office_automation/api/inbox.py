# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Whitelisted endpoints backing the Cartable (Inbox) SPA and its folders."""

import frappe
from frappe import _

from office_automation.office_automation.permissions.delegation import get_effective_users

OPEN_STATUSES = ("Unseen", "Seen")

# Inbox folder key -> referral_type value. "all" means no type filter.
INBOX_FOLDERS = {
	"all": None,
	"order": "Order",
	"followup": "Follow-up",
	"action": "Action",
	"notification": "Notification",
	"info": "Info",
}

REFERRAL_FIELDS = [
	"name",
	"reference_doctype",
	"reference_name",
	"sender",
	"recipient",
	"action_type",
	"referral_type",
	"instruction",
	"status",
	"outcome",
	"is_cc",
	"is_overdue",
	"parent_referral",
	"creation",
	"modified",
]


def _enrich(rows: list[dict]) -> list[dict]:
	"""Attach the referenced document's title (+ letter metadata) for display.

	Batches lookups per doctype to avoid N+1 queries.
	"""
	by_doctype: dict[str, set] = {}
	for row in rows:
		by_doctype.setdefault(row["reference_doctype"], set()).add(row["reference_name"])

	meta_map: dict[tuple, dict] = {}
	for doctype, names in by_doctype.items():
		fields = ["name"]
		meta = frappe.get_meta(doctype)
		title_field = (meta.get_title_field() if meta else None) or "name"
		if title_field != "name":
			fields.append(f"{title_field} as _title")
		if doctype == "Automation Letter":
			fields += ["urgency", "confidentiality", "is_private", "date as letter_date"]
		records = frappe.get_all(
			doctype, filters={"name": ["in", list(names)]}, fields=fields, ignore_permissions=True
		)
		for rec in records:
			meta_map[(doctype, rec["name"])] = rec

	for row in rows:
		rec = meta_map.get((row["reference_doctype"], row["reference_name"]), {})
		row["reference_title"] = rec.get("_title") or row["reference_name"]
		row["urgency"] = rec.get("urgency")
		row["confidentiality"] = rec.get("confidentiality")
		row["is_private"] = rec.get("is_private")
		row["letter_date"] = rec.get("letter_date")
	return rows


def _recipients_for(user: str | None) -> list[str]:
	user = user or frappe.session.user
	if user != frappe.session.user and user not in get_effective_users(frappe.session.user):
		frappe.throw(_("You can only access your own inbox."), frappe.PermissionError)
	return get_effective_users(user) if user == frappe.session.user else [user]


# --------------------------------------------------------------------------- #
# Inbox (received)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_inbox_items(user: str | None = None, folder: str = "all") -> list[dict]:
	"""Open inbox items for the user, optionally filtered by folder.

	``folder`` is one of: all, order, followup, action, notification, info.
	Returns ``Document Referral`` rows where the user (or a delegator they
	substitute for) is the recipient and the status is not ``Actioned``.
	"""
	recipients = _recipients_for(user)
	filters = {"recipient": ["in", recipients], "status": ["in", OPEN_STATUSES]}

	referral_type = INBOX_FOLDERS.get(folder)
	if referral_type:
		filters["referral_type"] = referral_type

	rows = frappe.get_all(
		"Document Referral",
		filters=filters,
		fields=REFERRAL_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich(rows)


@frappe.whitelist()
def get_yic_items(user: str | None = None) -> list[dict]:
	"""YIC Inbox — a department/workflow folder.

	Custom query logic: open inbox items whose referenced Automation Letter is
	tagged for the YIC workflow (``letter_type == "YIC"``). Adjust the rule here
	to match your organisation's routing.
	"""
	recipients = _recipients_for(user)
	yic_letters = frappe.get_all(
		"Automation Letter", filters={"letter_type": "YIC"}, pluck="name", ignore_permissions=True
	)
	if not yic_letters:
		return []
	rows = frappe.get_all(
		"Document Referral",
		filters={
			"recipient": ["in", recipients],
			"status": ["in", OPEN_STATUSES],
			"reference_doctype": "Automation Letter",
			"reference_name": ["in", yic_letters],
		},
		fields=REFERRAL_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich(rows)


# --------------------------------------------------------------------------- #
# Outbox (sent)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_outbox_items(user: str | None = None, state: str = "all") -> list[dict]:
	"""Referrals sent by the user. ``state``: all | in_progress | approved | rejected."""
	senders = _recipients_for(user)
	filters = {"sender": ["in", senders]}

	if state == "in_progress":
		filters["status"] = ["in", OPEN_STATUSES]
	elif state == "approved":
		filters["outcome"] = "Approved"
	elif state == "rejected":
		filters["outcome"] = "Rejected"

	rows = frappe.get_all(
		"Document Referral",
		filters=filters,
		fields=REFERRAL_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich(rows)


# --------------------------------------------------------------------------- #
# Letters (drafts / visibility)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_drafts(user: str | None = None) -> list[dict]:
	"""Unsubmitted letters owned by the user (docstatus == 0)."""
	owners = _recipients_for(user)
	return frappe.get_all(
		"Automation Letter",
		filters={"docstatus": 0, "owner": ["in", owners]},
		fields=[
			"name",
			"subject",
			"letter_no",
			"date",
			"letter_type",
			"urgency",
			"confidentiality",
			"is_private",
			"status",
			"modified",
		],
		order_by="modified desc",
	)


@frappe.whitelist()
def get_letters_by_visibility(visibility: str = "public") -> list[dict]:
	"""Letters filtered by the private/public flag.

	Uses ``frappe.get_list`` (not ``get_all``) so the delegation
	``permission_query_conditions`` and row-level permissions apply — callers
	only ever see letters they are entitled to (their own or ones they are a
	party to). Privileged roles see all.
	"""
	is_private = 1 if visibility == "private" else 0
	return frappe.get_list(
		"Automation Letter",
		filters={"is_private": is_private, "docstatus": ["!=", 2]},
		fields=[
			"name",
			"subject",
			"letter_no",
			"date",
			"letter_type",
			"urgency",
			"confidentiality",
			"is_private",
			"status",
			"sender",
			"modified",
		],
		order_by="modified desc",
		limit_page_length=0,
	)


# --------------------------------------------------------------------------- #
# Counts for the sidebar badges
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_folder_counts(user: str | None = None) -> dict:
	"""Badge counts for every sidebar folder."""
	recipients = _recipients_for(user)

	def inbox_count(referral_type=None):
		f = {"recipient": ["in", recipients], "status": ["in", OPEN_STATUSES]}
		if referral_type:
			f["referral_type"] = referral_type
		return frappe.db.count("Document Referral", f)

	inbox = {key: inbox_count(rt) for key, rt in INBOX_FOLDERS.items()}

	outbox = {
		"all": frappe.db.count("Document Referral", {"sender": ["in", recipients]}),
		"in_progress": frappe.db.count(
			"Document Referral", {"sender": ["in", recipients], "status": ["in", OPEN_STATUSES]}
		),
		"approved": frappe.db.count(
			"Document Referral", {"sender": ["in", recipients], "outcome": "Approved"}
		),
		"rejected": frappe.db.count(
			"Document Referral", {"sender": ["in", recipients], "outcome": "Rejected"}
		),
	}

	drafts = frappe.db.count("Automation Letter", {"docstatus": 0, "owner": ["in", recipients]})

	return {"inbox": inbox, "outbox": outbox, "drafts": drafts}


@frappe.whitelist()
def get_menu_items() -> list[dict]:
	"""Admin-configurable shortcuts for the Inbox left menu.

	Managed in Office Automation Settings → Menu Items. Falls back to a sensible
	default set when none are configured.
	"""
	settings = frappe.get_cached_doc("Office Automation Settings")
	items = [
		{"label": m.label, "icon": m.icon or "folder", "link_type": m.link_type, "link_to": m.link_to}
		for m in (settings.menu_items or [])
	]
	if items:
		return items
	return [
		{
			"label": "نامه‌های اتوماسیون",
			"icon": "file-text",
			"link_type": "DocType",
			"link_to": "Automation Letter",
		},
		{"label": "ارجاعات", "icon": "forward", "link_type": "DocType", "link_to": "Document Referral"},
		{"label": "قانون تفویض", "icon": "users", "link_type": "DocType", "link_to": "Delegation Rule"},
		{
			"label": "تنظیمات",
			"icon": "settings",
			"link_type": "DocType",
			"link_to": "Office Automation Settings",
		},
	]


@frappe.whitelist()
def get_dashboard_stats(user: str | None = None) -> dict:
	"""Headline numbers for the dashboard cards."""
	recipients = _recipients_for(user)
	base = {"recipient": ["in", recipients]}

	unseen = frappe.db.count("Document Referral", {**base, "status": "Unseen"})
	pending = frappe.db.count("Document Referral", {**base, "status": "Seen"})
	overdue = frappe.db.count("Document Referral", {**base, "is_overdue": 1, "status": ["in", OPEN_STATUSES]})
	today = frappe.db.count("Document Referral", {**base, "creation": [">=", frappe.utils.today()]})
	return {"unseen": unseen, "pending": pending, "overdue": overdue, "today": today}
