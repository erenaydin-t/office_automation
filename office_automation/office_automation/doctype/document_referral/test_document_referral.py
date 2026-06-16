# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from office_automation.office_automation.doctype.document_referral.document_referral import (
	approve_referral,
	forward_document,
	get_referral_tree,
	reject_referral,
)

OA_USER_ROLE = "Office Automation User"


def ensure_oa_user(email: str) -> str:
	"""Create (or fetch) an enabled user holding the Office Automation User role.

	The referral engine requires the *forwarding* user to have read access to the
	referenced document, which — by design — flows from this role plus being on a
	referral of the document.
	"""
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"enabled": 1,
				"roles": [{"role": OA_USER_ROLE}],
			}
		).insert(ignore_permissions=True)
	elif not frappe.db.exists("Has Role", {"parent": email, "role": OA_USER_ROLE}):
		user = frappe.get_doc("User", email)
		user.add_roles(OA_USER_ROLE)
	return email


class TestDocumentReferral(FrappeTestCase):
	def setUp(self):
		self.user1 = ensure_oa_user("test1@example.com")
		self.user2 = ensure_oa_user("test2@example.com")

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

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_forward_and_tree(self):
		# Administrator -> test1
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "Please review")

		# test1 (an Office Automation User who is on ref1) -> test2, as a child of ref1
		frappe.set_user(self.user1)
		ref2 = forward_document(
			"Automation Letter",
			self.letter.name,
			self.user2,
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

	def test_forwarding_user_without_access_is_blocked(self):
		# A bare user with no role and no referral cannot forward the letter.
		stranger = "stranger@example.com"
		if not frappe.db.exists("User", stranger):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": stranger,
					"first_name": "stranger",
					"send_welcome_email": 0,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)

		frappe.set_user(stranger)
		with self.assertRaises(frappe.PermissionError):
			forward_document("Automation Letter", self.letter.name, self.user1, "No access")

	def test_approve_sets_outcome(self):
		ref = forward_document(
			"Automation Letter", self.letter.name, self.user1, "Please approve", referral_type="Action"
		)
		frappe.set_user(self.user1)
		approve_referral(ref, note="Looks good")
		frappe.set_user("Administrator")
		row = frappe.db.get_value("Document Referral", ref, ["status", "outcome"], as_dict=True)
		self.assertEqual(row.status, "Actioned")
		self.assertEqual(row.outcome, "Approved")

	def test_reject_sets_outcome(self):
		ref = forward_document(
			"Automation Letter", self.letter.name, self.user1, "Please review", referral_type="Action"
		)
		frappe.set_user(self.user1)
		reject_referral(ref, note="Needs rework")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "outcome"), "Rejected")
