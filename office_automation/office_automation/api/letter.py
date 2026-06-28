# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Whitelisted endpoints for composing letters from the modern New Letter UI."""

import frappe
from frappe import _


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
		_link_file(a.get("file_url"), doc.name)

	if int(submit or 0):
		doc.submit()

	frappe.db.commit()
	return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


def _apply_letter_payload(doc, data: dict):
	"""Populate an Automation Letter doc (new or existing draft) from a composer
	payload. Child tables are cleared and rebuilt so edits are not duplicated."""
	doc.subject = data.get("subject")
	doc.body = data.get("body")
	doc.date = data.get("date") or frappe.utils.today()
	# Fall back to the doc's existing/defaulted value so the field default
	# ("نامه داخلی") still applies when a caller omits the type. Guard against a
	# missing/renamed Letter Type so a stale default never blocks letter creation.
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
def get_letter_detail(name: str) -> dict:
	"""Full letter payload for the panel's letter view: header, body, attachments
	and the referral flow (with full names, action and timestamps)."""
	letter = frappe.get_doc("Automation Letter", name)
	letter.check_permission("read")

	referrals = frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": "Automation Letter", "reference_name": name},
		fields=[
			"name",
			"sender",
			"recipient",
			"referral_type",
			"action_type",
			"instruction",
			"status",
			"outcome",
			"is_cc",
			"seen_on",
			"creation",
		],
		order_by="creation asc",
	)
	# The sender may recall (unsend) a referral only while it is still unseen.
	is_sender = letter.sender == frappe.session.user
	unseen_count = 0
	for r in referrals:
		r["sender_name"] = frappe.utils.get_fullname(r["sender"])
		r["recipient_name"] = frappe.utils.get_fullname(r["recipient"])
		r["can_recall"] = bool(is_sender and r["status"] == "Unseen")
		if r["status"] == "Unseen":
			unseen_count += 1

	return {
		"is_sender": is_sender,
		"can_recall": bool(is_sender and unseen_count),
		"unseen_count": unseen_count,
		"name": letter.name,
		"subject": letter.subject,
		"letter_no": letter.letter_no,
		"date": letter.date,
		"sender": letter.sender,
		"sender_name": frappe.utils.get_fullname(letter.sender),
		"body": letter.body,
		"status": letter.status,
		"letter_type": letter.letter_type,
		"confidentiality": letter.confidentiality,
		"urgency": letter.urgency,
		"is_private": letter.is_private,
		"attachments": [{"title": a.title, "attachment": a.attachment} for a in letter.attachments],
		"referrals": referrals,
	}


def _link_file(file_url: str | None, docname: str):
	if not file_url:
		return
	file_name = frappe.db.get_value(
		"File", {"file_url": file_url, "attached_to_name": ["in", ["", None]]}, "name"
	)
	if file_name:
		frappe.db.set_value(
			"File",
			file_name,
			{"attached_to_doctype": "Automation Letter", "attached_to_name": docname},
			update_modified=False,
		)
