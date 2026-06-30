# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from office_automation.office_automation.doctype.document_referral.document_referral import (
	approve_referral,
	forward_document,
	get_referral_tree,
	mark_referral_seen,
	recall_letter,
	recall_referral,
	reject_referral,
	return_referral,
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
				# Must be a System User for desk DocType permissions to apply.
				"user_type": "System User",
				"roles": [{"role": OA_USER_ROLE}],
			}
		).insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)
		if user.user_type != "System User":
			user.user_type = "System User"
			user.save(ignore_permissions=True)
		if not frappe.db.exists("Has Role", {"parent": email, "role": OA_USER_ROLE}):
			user.add_roles(OA_USER_ROLE)

	# Drop cached roles/permissions so the new role takes effect immediately.
	frappe.clear_cache(user=email)
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

	def test_return_sets_outcome(self):
		ref = forward_document(
			"Automation Letter", self.letter.name, self.user1, "Please revise", referral_type="Action"
		)
		frappe.set_user(self.user1)
		return_referral(ref, note="Returned for correction")
		frappe.set_user("Administrator")
		row = frappe.db.get_value("Document Referral", ref, ["status", "outcome"], as_dict=True)
		self.assertEqual(row.status, "Actioned")
		self.assertEqual(row.outcome, "Returned")

	def test_sender_cannot_action_own_referral(self):
		"""A sender must not approve/reject/return a referral they sent — only the
		recipient (or a delegate) may action it (security review fix)."""
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "Please review")
		frappe.set_user(self.user1)
		# user1 forwards to user2: user1 is now the SENDER of ref2, user2 the recipient.
		ref2 = forward_document(
			"Automation Letter", self.letter.name, self.user2, "Please action", parent_referral=ref1
		)
		# As the sender, user1 must be blocked from every outcome action on ref2.
		for action in (approve_referral, reject_referral, return_referral):
			with self.assertRaises(frappe.PermissionError):
				action(ref2)
		frappe.set_user("Administrator")
		# The referral is untouched: still open, outcome still Pending.
		row = frappe.db.get_value("Document Referral", ref2, ["status", "outcome"], as_dict=True)
		self.assertEqual(row.outcome, "Pending")
		self.assertNotEqual(row.status, "Actioned")

	# ------------------------------------------------------------------ #
	# Recall (بازپس‌گیری)
	# ------------------------------------------------------------------ #
	def test_recall_unread_reverts_letter_to_draft(self):
		"""When nothing was opened, recall removes every referral and the
		letter falls back to an editable Draft (docstatus 0)."""
		forward_document("Automation Letter", self.letter.name, self.user1, "a")
		forward_document("Automation Letter", self.letter.name, self.user2, "b")

		res = recall_letter(self.letter.name)
		self.assertEqual(res["recalled"], 2)
		self.assertEqual(res["kept"], 0)
		self.assertTrue(res["reverted_to_draft"])

		self.assertEqual(
			frappe.db.count(
				"Document Referral",
				{"reference_doctype": "Automation Letter", "reference_name": self.letter.name},
			),
			0,
		)
		row = frappe.db.get_value(
			"Automation Letter", self.letter.name, ["docstatus", "status"], as_dict=True
		)
		self.assertEqual(row.docstatus, 0)
		self.assertEqual(row.status, "Draft")

	def test_recall_keeps_opened_referrals(self):
		"""A recipient who already opened the letter keeps it; the letter stays
		submitted and only the unread referral is pulled back."""
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "a")
		ref2 = forward_document("Automation Letter", self.letter.name, self.user2, "b")

		frappe.set_user(self.user1)
		mark_referral_seen(ref1)
		frappe.set_user("Administrator")

		res = recall_letter(self.letter.name)
		self.assertEqual(res["recalled"], 1)
		self.assertEqual(res["kept"], 1)
		self.assertFalse(res["reverted_to_draft"])

		self.assertTrue(frappe.db.exists("Document Referral", ref1))
		self.assertFalse(frappe.db.exists("Document Referral", ref2))
		self.assertEqual(frappe.db.get_value("Automation Letter", self.letter.name, "docstatus"), 1)

	def test_recall_blocked_when_all_opened(self):
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "a")
		frappe.set_user(self.user1)
		mark_referral_seen(ref1)
		frappe.set_user("Administrator")

		with self.assertRaises(frappe.ValidationError):
			recall_letter(self.letter.name)

	def test_recall_single_referral(self):
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "a")
		res = recall_referral(ref1)
		self.assertTrue(res["reverted_to_draft"])
		self.assertFalse(frappe.db.exists("Document Referral", ref1))

	def test_recall_single_referral_blocked_when_opened(self):
		ref1 = forward_document("Automation Letter", self.letter.name, self.user1, "a")
		frappe.set_user(self.user1)
		mark_referral_seen(ref1)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			recall_referral(ref1)

	def test_only_sender_can_recall(self):
		forward_document("Automation Letter", self.letter.name, self.user1, "a")
		frappe.set_user(self.user1)
		try:
			with self.assertRaises(frappe.PermissionError):
				recall_letter(self.letter.name)
		finally:
			frappe.set_user("Administrator")

	def test_cannot_read_another_users_cartable(self):
		"""Folder endpoints must reject requests for another user's data."""
		from office_automation.office_automation.api.inbox import (
			get_drafts,
			get_folder_counts,
			get_outbox_items,
		)

		ensure_oa_user(self.user1)
		frappe.set_user(self.user1)
		try:
			for call in (get_outbox_items, get_drafts, get_folder_counts):
				with self.assertRaises(frappe.PermissionError):
					call(user="Administrator")
		finally:
			frappe.set_user("Administrator")
