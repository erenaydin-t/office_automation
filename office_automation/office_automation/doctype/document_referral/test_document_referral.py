# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from office_automation.office_automation.doctype.document_referral.document_referral import (
	forward_document,
	get_referral_tree,
)


class TestDocumentReferral(FrappeTestCase):
	def setUp(self):
		self.letter = frappe.get_doc(
			{
				"doctype": "Automation Letter",
				"subject": "Referral Test",
				"date": frappe.utils.today(),
				"sender": "Administrator",
				"body": "<p>Body</p>",
			}
		).insert(ignore_permissions=True)
		self.letter.submit()

	def test_forward_and_tree(self):
		# Administrator -> test1
		ref1 = forward_document("Automation Letter", self.letter.name, "test1@example.com", "Please review")
		# test1 -> test2 (child of ref1)
		frappe.set_user("test1@example.com")
		ref2 = forward_document(
			"Automation Letter",
			self.letter.name,
			"test2@example.com",
			"Please action",
			parent_referral=ref1,
		)
		frappe.set_user("Administrator")

		tree = get_referral_tree("Automation Letter", self.letter.name)
		self.assertEqual(len(tree), 1)
		self.assertEqual(tree[0]["name"], ref1)
		self.assertEqual(len(tree[0]["children"]), 1)
		self.assertEqual(tree[0]["children"][0]["name"], ref2)

		# Parent should be Actioned because test1 forwarded it onward.
		self.assertEqual(frappe.db.get_value("Document Referral", ref1, "status"), "Actioned")
