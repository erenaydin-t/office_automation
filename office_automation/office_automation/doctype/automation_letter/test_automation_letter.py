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
