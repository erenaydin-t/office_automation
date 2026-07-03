# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Whitelisted endpoints backing the Cartable (Inbox) SPA and its folders."""

import frappe
from frappe import _
from frappe.query_builder.functions import Count

from office_automation.office_automation.permissions.delegation import get_effective_users

OPEN_STATUSES = ("Unseen", "Seen")
OPEN_STATUS_LIST = list(OPEN_STATUSES)

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
def get_inbox_items(
	user: str | None = None, folder: str = "all", limit: int | None = None
) -> list[dict]:
	"""Open inbox items for the user, optionally filtered by folder.

	``folder`` is one of: all, order, followup, action, notification, info.
	``limit`` caps the number of rows (e.g. the dashboard preview needs only a
	handful); omit it to return the full folder.
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
		limit_page_length=int(limit) if limit else 0,
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
	"""Referrals sent by the user. ``state``: all | in_progress | approved | rejected | returned."""
	senders = _recipients_for(user)
	filters = {"sender": ["in", senders]}

	if state == "in_progress":
		filters["status"] = ["in", OPEN_STATUSES]
	elif state == "approved":
		filters["outcome"] = "Approved"
	elif state == "rejected":
		filters["outcome"] = "Rejected"
	elif state == "returned":
		filters["outcome"] = "Returned"

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
	"""Badge counts for every sidebar folder.

	Uses one grouped aggregate query per pane (inbox, outbox) instead of a
	``COUNT`` per folder, so the whole sidebar refreshes in a few round-trips.
	"""
	recipients = _recipients_for(user)

	DR = frappe.qb.DocType("Document Referral")

	# --- Inbox: open referrals grouped by type; "all" is the row total. ---
	inbox = {key: 0 for key in INBOX_FOLDERS}
	type_to_folder = {rt: key for key, rt in INBOX_FOLDERS.items() if rt}
	inbox_rows = (
		frappe.qb.from_(DR)
		.select(DR.referral_type, Count(DR.name).as_("cnt"))
		.where(DR.recipient.isin(recipients) & DR.status.isin(OPEN_STATUS_LIST))
		.groupby(DR.referral_type)
	).run(as_dict=True)
	for row in inbox_rows:
		inbox["all"] += row["cnt"]
		key = type_to_folder.get(row["referral_type"])
		if key:
			inbox[key] += row["cnt"]

	# --- Outbox: everything sent, grouped by (outcome, status) in one pass. ---
	outbox = {"all": 0, "in_progress": 0, "approved": 0, "rejected": 0, "returned": 0}
	outcome_key = {"Approved": "approved", "Rejected": "rejected", "Returned": "returned"}
	outbox_rows = (
		frappe.qb.from_(DR)
		.select(DR.outcome, DR.status, Count(DR.name).as_("cnt"))
		.where(DR.sender.isin(recipients))
		.groupby(DR.outcome, DR.status)
	).run(as_dict=True)
	for row in outbox_rows:
		outbox["all"] += row["cnt"]
		if row["status"] in OPEN_STATUSES:
			outbox["in_progress"] += row["cnt"]
		key = outcome_key.get(row["outcome"])
		if key:
			outbox[key] += row["cnt"]

	drafts = frappe.db.count("Automation Letter", {"docstatus": 0, "owner": ["in", recipients]})

	return {"inbox": inbox, "outbox": outbox, "drafts": drafts}


@frappe.whitelist()
def get_dashboard_stats(user: str | None = None) -> dict:
	"""Headline numbers for the dashboard cards.

	Also returns ``recipients`` — the effective recipient set (the user plus
	anyone they substitute for) — so the client can build drill-down list
	filters that match these counts exactly, including under delegation.
	"""
	recipients = _recipients_for(user)

	# unseen / pending / overdue all derive from the open-referral set, so a
	# single query grouped by (status, is_overdue) covers all three.
	unseen = pending = overdue = 0
	DR = frappe.qb.DocType("Document Referral")
	stat_rows = (
		frappe.qb.from_(DR)
		.select(DR.status, DR.is_overdue, Count(DR.name).as_("cnt"))
		.where(DR.recipient.isin(recipients) & DR.status.isin(OPEN_STATUS_LIST))
		.groupby(DR.status, DR.is_overdue)
	).run(as_dict=True)
	for row in stat_rows:
		if row["status"] == "Unseen":
			unseen += row["cnt"]
		elif row["status"] == "Seen":
			pending += row["cnt"]
		if row["is_overdue"]:
			overdue += row["cnt"]

	today = frappe.db.count(
		"Document Referral",
		{"recipient": ["in", recipients], "creation": [">=", frappe.utils.today()]},
	)
	return {
		"unseen": unseen,
		"pending": pending,
		"overdue": overdue,
		"today": today,
		"recipients": recipients,
	}


# Dashboard stat key -> extra Document Referral filters. Each mirrors the
# predicate counted in get_dashboard_stats so the drilled-in list matches the
# number on the card exactly.
STAT_FILTERS = {
	"unseen": {"status": "Unseen"},
	"pending": {"status": "Seen"},
	"overdue": {"is_overdue": 1, "status": ["in", OPEN_STATUS_LIST]},
	# ``today`` is filled in per-request (needs today's date).
	"today": {},
}


@frappe.whitelist()
def get_referrals_by_stat(kind: str, user: str | None = None) -> list[dict]:
	"""Referral rows behind a dashboard stat card (unseen / pending / overdue /
	today), enriched for the Cartable list — same shape as ``get_inbox_items`` so
	the SPA can render them inline instead of routing out to a desk list view.
	"""
	if kind not in STAT_FILTERS:
		frappe.throw(_("Unknown dashboard stat: {0}").format(kind))

	recipients = _recipients_for(user)
	filters = {"recipient": ["in", recipients], **STAT_FILTERS[kind]}
	if kind == "today":
		filters["creation"] = [">=", frappe.utils.today()]

	rows = frappe.get_all(
		"Document Referral",
		filters=filters,
		fields=REFERRAL_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich(rows)
