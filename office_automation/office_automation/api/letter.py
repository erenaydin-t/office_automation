# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Whitelisted endpoints for composing letters from the modern New Letter UI."""

import frappe
from frappe import _

from office_automation.office_automation.doctype.document_referral.document_referral import (
	OPEN_STATUSES,
	link_file_to_document,
)
from office_automation.office_automation.permissions.delegation import get_effective_users


@frappe.whitelist()
def create_letter(payload: str, submit: int = 0) -> dict:
	"""Create an Automation Letter from the SPA composer.

	``payload`` is a JSON object with: subject, body, date, letter_type,
	confidentiality, urgency, is_private, recipients[], cc[], attachments[].
	When ``submit`` is truthy the letter is registered and delivered.
	"""
	data = frappe.parse_json(payload)

	if not (data.get("subject") or "").strip():
		frappe.throw(_("Subject is mandatory."))

	doc = frappe.new_doc("Automation Letter")
	_apply_letter_payload(doc, data)

	# Respects role permissions (Office Automation User has create).
	doc.insert()

	return _finalize_letter(doc, data, submit)


@frappe.whitelist()
def update_letter(name: str, payload: str, submit: int = 0) -> dict:
	"""Update an existing **draft** Automation Letter from the SPA composer.

	Only letters still in draft (``docstatus == 0``) may be edited. Accepts the
	same ``payload`` shape as :func:`create_letter`; recipient/CC/attachment
	tables are fully rebuilt from it. When ``submit`` is truthy the draft is
	registered and delivered.
	"""
	data = frappe.parse_json(payload)

	if not (data.get("subject") or "").strip():
		frappe.throw(_("Subject is mandatory."))

	doc = frappe.get_doc("Automation Letter", name)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft letters can be edited."))
	doc.check_permission("write")

	_apply_letter_payload(doc, data)
	doc.save()

	return _finalize_letter(doc, data, submit)


def _finalize_letter(doc, data: dict, submit) -> dict:
	"""Shared tail for create/update: re-link uploaded files to the saved letter,
	optionally submit (register + deliver), commit, and return the SPA result."""
	for a in data.get("attachments") or []:
		link_file_to_document(a.get("file_url"), "Automation Letter", doc.name)

	if int(submit or 0):
		doc.submit()

	frappe.db.commit()
	# on_submit moves the letter Registered -> In Progress straight in the DB, so
	# report the persisted status rather than the stale in-memory one.
	status = frappe.db.get_value("Automation Letter", doc.name, "status")
	return {"name": doc.name, "docstatus": doc.docstatus, "status": status, "letter_no": doc.letter_no}


def _apply_letter_payload(doc, data: dict):
	"""Populate an Automation Letter doc (new or existing draft) from a composer
	payload. Child tables are cleared and rebuilt so edits are not duplicated."""
	doc.subject = data.get("subject")
	doc.body = data.get("body")
	doc.date = data.get("date") or frappe.utils.today()
	# New-letter type defaults are applied by Automation Letter.before_insert
	# (configurable via Office Automation Settings); preserve an existing value
	# when a caller omits it on edit. A stale/renamed type is dropped to None so
	# it never blocks creation with a link-validation error.
	letter_type = data.get("letter_type") or doc.letter_type or None
	if letter_type and not frappe.db.exists("Letter Type", letter_type):
		letter_type = None
	doc.letter_type = letter_type
	doc.confidentiality = data.get("confidentiality") or "Normal"
	doc.urgency = data.get("urgency") or "Normal"
	doc.is_private = 1 if data.get("is_private") else 0

	doc.set("recipients", [])
	for r in data.get("recipients") or []:
		if not r.get("recipient"):
			continue
		doc.append(
			"recipients",
			{
				"recipient": r["recipient"],
				"referral_type": r.get("referral_type") or "Action",
				"action_type": r.get("action_type"),
				"instruction": r.get("instruction"),
			},
		)

	doc.set("cc_recipients", [])
	for c in data.get("cc") or []:
		if c.get("recipient"):
			doc.append("cc_recipients", {"recipient": c["recipient"], "referral_type": "Info"})

	doc.set("attachments", [])
	for a in data.get("attachments") or []:
		if a.get("file_url"):
			doc.append("attachments", {"title": a.get("title"), "attachment": a["file_url"]})


@frappe.whitelist()
def get_default_letter_type() -> str | None:
	"""The org's configured default Letter Type for new letters (or None).

	Whitelisted so the composer can pre-select it without the user needing read
	access to Office Automation Settings.
	"""
	from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
		get_settings,
	)

	default_type = get_settings().default_letter_type
	if default_type and frappe.db.exists("Letter Type", default_type):
		return default_type
	return None


@frappe.whitelist()
def get_letter_for_edit(name: str) -> dict:
	"""Editable payload for a draft letter: scalar fields plus the recipient, CC
	and attachment rows the composer needs to prefill."""
	doc = frappe.get_doc("Automation Letter", name)
	doc.check_permission("read")
	if doc.docstatus != 0:
		frappe.throw(_("Only draft letters can be edited."))

	return {
		"name": doc.name,
		"subject": doc.subject,
		"body": doc.body,
		"date": doc.date,
		"letter_type": doc.letter_type,
		"confidentiality": doc.confidentiality,
		"urgency": doc.urgency,
		"is_private": doc.is_private,
		"recipients": [
			{
				"recipient": r.recipient,
				"recipient_name": r.recipient_name or frappe.utils.get_fullname(r.recipient),
				"referral_type": r.referral_type,
				"action_type": r.action_type,
				"instruction": r.instruction,
			}
			for r in doc.recipients
		],
		"cc": [
			{
				"recipient": c.recipient,
				"recipient_name": c.recipient_name or frappe.utils.get_fullname(c.recipient),
			}
			for c in doc.cc_recipients
		],
		"attachments": [{"title": a.title, "file_url": a.attachment} for a in doc.attachments],
	}


@frappe.whitelist()
def get_letter_detail(name: str, mark_seen: int = 1) -> dict:
	"""Full letter payload for the panel's letter view: header, body, attachments
	and the referral flow (with full names, action and timestamps).

	Also resolves ``my_referral`` — the caller's own open referral on this letter
	(or one addressed to someone they currently substitute for) — which drives
	the approve / reject / return / done / forward actions in the UI. Opening the
	letter counts as reading it, so that referral is marked ``Seen`` (unless
	``mark_seen`` is 0), wherever the letter was opened from.
	"""
	letter = frappe.get_doc("Automation Letter", name)
	letter.check_permission("read")

	referrals = frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": "Automation Letter", "reference_name": name},
		fields=[
			"name",
			"parent_referral",
			"sender",
			"recipient",
			"referral_type",
			"action_type",
			"instruction",
			"attachment",
			"status",
			"outcome",
			"is_cc",
			"is_overdue",
			"seen_on",
			"actioned_on",
			"creation",
		],
		order_by="creation asc",
	)

	user = frappe.session.user
	effective = get_effective_users(user)

	# The caller's actionable item: own first, then delegated; newest first.
	mine = [r for r in referrals if r["recipient"] in effective and r["status"] in OPEN_STATUSES]
	mine.sort(key=lambda r: (r["recipient"] != user, -_ts(r["creation"])))
	my_referral = mine[0] if mine else None

	if my_referral and my_referral["status"] == "Unseen" and int(mark_seen or 0):
		frappe.get_doc("Document Referral", my_referral["name"]).mark_seen()
		my_referral["status"] = "Seen"
		my_referral["seen_on"] = frappe.utils.now_datetime()

	# The sender may recall (unsend) a referral only while it is still unseen.
	is_sender = letter.sender == user
	unseen_count = 0
	names = _full_names({r["sender"] for r in referrals} | {r["recipient"] for r in referrals})
	for r in referrals:
		r["sender_name"] = names.get(r["sender"]) or r["sender"]
		r["recipient_name"] = names.get(r["recipient"]) or r["recipient"]
		# Anyone may pull back a referral *they* sent while it is still unread.
		r["can_recall"] = bool(r["sender"] == user and r["status"] == "Unseen")
		if r["status"] == "Unseen" and r["sender"] == letter.sender:
			unseen_count += 1

	return {
		"is_sender": is_sender,
		"can_recall": bool(is_sender and unseen_count),
		"unseen_count": unseen_count,
		"my_referral": (
			{
				"name": my_referral["name"],
				"recipient": my_referral["recipient"],
				"recipient_name": my_referral.get("recipient_name"),
				"referral_type": my_referral["referral_type"],
				"is_cc": my_referral["is_cc"],
				"on_behalf_of": my_referral["recipient"] if my_referral["recipient"] != user else None,
			}
			if my_referral
			else None
		),
		"name": letter.name,
		"subject": letter.subject,
		"letter_no": letter.letter_no,
		"date": letter.date,
		"sender": letter.sender,
		"sender_name": frappe.utils.get_fullname(letter.sender),
		"body": letter.body,
		"status": letter.status,
		"docstatus": letter.docstatus,
		"letter_type": letter.letter_type,
		"confidentiality": letter.confidentiality,
		"urgency": letter.urgency,
		"is_private": letter.is_private,
		"attachments": [{"title": a.title, "attachment": a.attachment} for a in letter.attachments],
		"referrals": referrals,
	}


def _ts(value) -> float:
	"""Sortable timestamp for a datetime (or datetime string)."""
	try:
		return frappe.utils.get_datetime(value).timestamp()
	except Exception:
		return 0.0


def _full_names(users: set) -> dict:
	"""Batch-resolve user ids to full names (one query instead of N)."""
	users = [u for u in users if u]
	if not users:
		return {}
	rows = frappe.get_all(
		"User", filters={"name": ["in", users]}, fields=["name", "full_name"], ignore_permissions=True
	)
	return {r.name: r.full_name for r in rows}
