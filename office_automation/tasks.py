# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Scheduled background jobs for Office Automation."""

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

OPEN_STATUSES = ("Unseen", "Seen")


def daily():
	"""Entry point wired to the ``daily`` scheduler event."""
	flag_overdue_referrals()


def flag_overdue_referrals():
	"""Mark open referrals older than the SLA threshold as overdue.

	The threshold comes from ``Office Automation Settings``. Each newly overdue
	referral optionally triggers a reminder notification to its recipient.
	"""
	from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
		get_settings,
	)

	settings = get_settings()
	days = int(settings.overdue_after_days or 2)
	if days <= 0:
		return

	cutoff = add_to_date(now_datetime(), days=-days)

	referrals = frappe.get_all(
		"Document Referral",
		filters={
			"status": ["in", OPEN_STATUSES],
			"is_overdue": 0,
			"creation": ["<", cutoff],
		},
		fields=["name", "recipient", "sender", "reference_doctype", "reference_name"],
	)

	for ref in referrals:
		frappe.db.set_value("Document Referral", ref.name, "is_overdue", 1, update_modified=False)
		if settings.notify_on_overdue:
			_notify_overdue(ref)

	if referrals:
		frappe.db.commit()


def _notify_overdue(ref):
	try:
		subject = _("Overdue referral awaiting your action: {0} {1}").format(
			ref.reference_doctype, ref.reference_name
		)
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": ref.recipient,
				"type": "Alert",
				"document_type": "Document Referral",
				"document_name": ref.name,
			}
		).insert(ignore_permissions=True)
		frappe.publish_realtime(
			event="oa_inbox_update",
			message={"referral": ref.name, "subject": subject, "overdue": True},
			user=ref.recipient,
			after_commit=True,
		)
	except Exception:
		frappe.log_error(title="office_automation: overdue notification failed")
