# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAutomationLetter(FrappeTestCase):
	def test_submit_sets_registered_status(self):
		letter = frappe.get_doc(
			{
				"doctype": "Automation Letter",
				"subject": "Test Letter",
				"date": frappe.utils.today(),
				"sender": "Administrator",
				"body": "<p>Hello</p>",
			}
		).insert(ignore_permissions=True)

		self.assertEqual(letter.status, "Draft")
		letter.submit()
		self.assertEqual(letter.status, "Registered")
		letter.cancel()
		self.assertEqual(letter.status, "Cancelled")

	def test_submit_sends_to_recipients(self):
		from office_automation.office_automation.doctype.document_referral.test_document_referral import (
			ensure_oa_user,
		)

		recipient = ensure_oa_user("test1@example.com")
		letter = frappe.get_doc(
			{
				"doctype": "Automation Letter",
				"subject": "Internal Send",
				"date": frappe.utils.today(),
				"sender": "Administrator",
				"body": "<p>Hello</p>",
				"recipients": [{"recipient": recipient, "instruction": "Please review"}],
			}
		).insert(ignore_permissions=True)
		letter.submit()

		# A root referral should now sit in the recipient's cartable.
		referrals = frappe.get_all(
			"Document Referral",
			filters={
				"reference_doctype": "Automation Letter",
				"reference_name": letter.name,
				"recipient": recipient,
			},
			fields=["name", "status", "parent_referral"],
		)
		self.assertEqual(len(referrals), 1)
		self.assertEqual(referrals[0].status, "Unseen")
		self.assertFalse(referrals[0].parent_referral)
		# Letter moves from Registered to In Progress once sent.
		self.assertEqual(frappe.db.get_value("Automation Letter", letter.name, "status"), "In Progress")

	def test_cannot_send_to_self(self):
		letter = frappe.get_doc(
			{
				"doctype": "Automation Letter",
				"subject": "Self Send",
				"date": frappe.utils.today(),
				"sender": "Administrator",
				"body": "<p>Hi</p>",
				"recipients": [{"recipient": "Administrator"}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			letter.insert(ignore_permissions=True)
