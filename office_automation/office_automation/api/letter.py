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
	doc.subject = data.get("subject")
	doc.body = data.get("body")
	doc.date = data.get("date") or frappe.utils.today()
	doc.letter_type = data.get("letter_type") or None
	doc.confidentiality = data.get("confidentiality") or "Normal"
	doc.urgency = data.get("urgency") or "Normal"
	doc.is_private = 1 if data.get("is_private") else 0

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

	for c in data.get("cc") or []:
		if c.get("recipient"):
			doc.append("cc_recipients", {"recipient": c["recipient"], "referral_type": "Info"})

	for a in data.get("attachments") or []:
		if a.get("file_url"):
			doc.append("attachments", {"title": a.get("title"), "attachment": a["file_url"]})

	# Respects role permissions (Office Automation User has create).
	doc.insert()

	# Re-point uploaded files to the saved letter so they appear in its sidebar.
	for a in data.get("attachments") or []:
		_link_file(a.get("file_url"), doc.name)

	if int(submit or 0):
		doc.submit()

	frappe.db.commit()
	return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.status}


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
