# Copyright (c) 2026, Milanpars and contributors
# See license.txt
"""Regression tests for the v0.5 fixes and features.

Covers: read-receipt integrity, delegate actions, auto-parenting on forward,
atomic multi-recipient forward, attachment access, cancel semantics,
secretariat numbering, recall scoping, archive folder, search and public
letter visibility.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from office_automation.office_automation.api.inbox import (
	get_folder_counts,
	get_inbox_items,
	search_letters,
)
from office_automation.office_automation.api.letter import create_letter, get_letter_detail
from office_automation.office_automation.doctype.automation_letter.automation_letter import (
	gregorian_to_jalali,
	make_letter_number,
)
from office_automation.office_automation.doctype.document_referral.document_referral import (
	approve_referral,
	forward_document,
	forward_to_many,
	mark_referral_actioned,
	mark_referral_seen,
	recall_letter,
	recall_referral,
)
from office_automation.office_automation.doctype.document_referral.test_document_referral import (
	ensure_oa_user,
)
from office_automation.office_automation.permissions.delegation import get_active_delegators

SETTINGS = "Office Automation Settings"


def _set_setting(field, value):
	frappe.db.set_single_value(SETTINGS, field, value)
	frappe.clear_document_cache(SETTINGS, SETTINGS)


class CartableTestBase(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.user1 = ensure_oa_user("test1@example.com")
		self.user2 = ensure_oa_user("test2@example.com")
		self.user3 = ensure_oa_user("test3@example.com")
		self.stranger = ensure_oa_user("stranger@example.com")
		self._settings_backup = {
			f: frappe.db.get_single_value(SETTINGS, f)
			for f in ("auto_letter_number", "letter_number_prefix", "public_letters_visible")
		}

	def tearDown(self):
		frappe.set_user("Administrator")
		for field, value in self._settings_backup.items():
			_set_setting(field, value)
		# The letter/referral APIs commit, so a changed setting may already be
		# durable — make the restore durable too or it leaks into other tests.
		frappe.db.commit()
		frappe.db.delete("Delegation Rule", {"delegator": self.user1})
		for u in (self.user1, self.user2, self.user3, self.stranger):
			frappe.cache().delete_value(f"oa_active_delegators::{u}")

	def _letter(self, sender=None, recipients=(), submit=True, **fields):
		"""Create (and submit) a letter as ``sender`` addressed to ``recipients``."""
		frappe.set_user(sender or self.user1)
		payload = {
			"subject": fields.pop("subject", "Cartable test"),
			"body": fields.pop("body", "<p>Body</p>"),
			"recipients": [{"recipient": r, "referral_type": "Action"} for r in recipients],
			**fields,
		}
		res = create_letter(json.dumps(payload), submit=1 if submit else 0)
		frappe.set_user("Administrator")
		return res["name"]

	def _referral(self, letter, recipient):
		return frappe.db.get_value(
			"Document Referral",
			{"reference_doctype": "Automation Letter", "reference_name": letter, "recipient": recipient},
			"name",
		)


class TestReadReceipts(CartableTestBase):
	def test_sender_cannot_mark_own_referral_seen(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)

		frappe.set_user(self.user1)  # the sender
		with self.assertRaises(frappe.PermissionError):
			mark_referral_seen(ref)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Unseen")

	def test_opening_letter_marks_recipients_item_seen(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)

		frappe.set_user(self.user2)
		detail = get_letter_detail(letter)
		self.assertEqual(detail["my_referral"]["name"], ref)
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Seen")

	def test_sender_opening_letter_does_not_mark_seen(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)

		frappe.set_user(self.user1)
		detail = get_letter_detail(letter)
		self.assertIsNone(detail["my_referral"])
		self.assertTrue(detail["can_recall"])
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Unseen")

	def test_mark_seen_can_be_disabled(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		get_letter_detail(letter, mark_seen=0)
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Unseen")


class TestDelegation(CartableTestBase):
	def _delegate(self, delegator, delegatee):
		return frappe.get_doc(
			{
				"doctype": "Delegation Rule",
				"delegator": delegator,
				"delegatee": delegatee,
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 5),
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

	def test_delegate_sees_and_actions_delegators_item(self):
		letter = self._letter(sender=self.user2, recipients=[self.user1])
		ref = self._referral(letter, self.user1)
		self._delegate(self.user1, self.user3)

		frappe.set_user(self.user3)
		detail = get_letter_detail(letter)
		self.assertEqual(detail["my_referral"]["name"], ref)
		self.assertEqual(detail["my_referral"]["on_behalf_of"], self.user1)
		approve_referral(ref, note="on behalf")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "outcome"), "Approved")

	def test_deleting_rule_revokes_access_immediately(self):
		rule = self._delegate(self.user1, self.user3)
		self.assertIn(self.user1, get_active_delegators(self.user3))  # warms the cache
		frappe.delete_doc("Delegation Rule", rule.name, ignore_permissions=True)
		self.assertNotIn(self.user1, get_active_delegators(self.user3))


class TestForwarding(CartableTestBase):
	def test_forward_without_parent_closes_callers_item(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)

		frappe.set_user(self.user2)
		child = forward_document("Automation Letter", letter, self.user3, "please handle")
		frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("Document Referral", child, "parent_referral"), ref)
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Actioned")

	def test_forward_to_many_shares_parent(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)

		frappe.set_user(self.user2)
		names = forward_to_many("Automation Letter", letter, json.dumps([self.user3, self.user1, self.user3]))
		frappe.set_user("Administrator")

		self.assertEqual(len(names), 2)  # duplicate collapsed
		parents = {frappe.db.get_value("Document Referral", n, "parent_referral") for n in names}
		self.assertEqual(parents, {ref})

	def test_forward_to_many_is_all_or_nothing(self):
		letter = self._letter(recipients=[self.user2])
		before = frappe.db.count("Document Referral", {"reference_name": letter})
		frappe.set_user(self.user2)
		with self.assertRaises(frappe.ValidationError):
			forward_to_many("Automation Letter", letter, [self.user3, "nobody@example.com"])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Document Referral", {"reference_name": letter}), before)

	def test_cannot_branch_from_someone_elses_referral(self):
		letter = self._letter(recipients=[self.user2, self.user3])
		ref_of_user2 = self._referral(letter, self.user2)

		frappe.set_user(self.user3)
		with self.assertRaises(frappe.PermissionError):
			forward_document("Automation Letter", letter, self.stranger, parent_referral=ref_of_user2)

	def test_new_referral_reopens_closed_letter(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		mark_referral_actioned(ref)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Automation Letter", letter, "status"), "Closed")

		frappe.set_user(self.user1)
		forward_document("Automation Letter", letter, self.user3)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Automation Letter", letter, "status"), "In Progress")

	def test_referral_attachment_is_downloadable_by_recipient(self):
		letter = self._letter(recipients=[self.user2])
		frappe.set_user(self.user2)
		f = frappe.get_doc(
			{"doctype": "File", "file_name": "note.txt", "content": b"hello", "is_private": 1}
		).insert()
		forward_to_many("Automation Letter", letter, [self.user3, self.stranger], attachment=f.file_url)
		frappe.set_user("Administrator")

		attached = frappe.db.get_value("File", f.name, ["attached_to_doctype", "attached_to_name"])
		self.assertEqual(tuple(attached), ("Automation Letter", letter))
		# Every recipient of the fan-out can open it, not just the first one.
		for user in (self.user3, self.stranger):
			frappe.set_user(user)
			self.assertTrue(frappe.get_doc("File", f.name).is_downloadable(), user)

	def test_action_note_is_stored_as_plain_text(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		approve_referral(ref, note='<img src=x onerror="alert(1)">ok')
		frappe.set_user("Administrator")
		instruction = frappe.db.get_value("Document Referral", ref, "instruction")
		self.assertNotIn("<img", instruction)
		self.assertIn("ok", instruction)


class TestRecall(CartableTestBase):
	def test_recall_letter_leaves_others_forwards_alone(self):
		letter = self._letter(recipients=[self.user2, self.user3])
		frappe.set_user(self.user2)
		mark_referral_seen(self._referral(letter, self.user2))
		child = forward_document("Automation Letter", letter, self.stranger)
		frappe.set_user(self.user1)
		res = recall_letter(letter)
		frappe.set_user("Administrator")

		self.assertEqual(res["recalled"], 1)  # only user3's unseen root referral
		self.assertTrue(frappe.db.exists("Document Referral", child))

	def test_recalling_a_forward_reopens_the_forwarders_item(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		child = forward_document("Automation Letter", letter, self.user3)
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Actioned")
		recall_referral(child)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Seen")


class TestCancel(CartableTestBase):
	def test_cancel_persists_status_and_clears_inboxes(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		doc = frappe.get_doc("Automation Letter", letter)
		doc.cancel()

		self.assertEqual(frappe.db.get_value("Automation Letter", letter, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Actioned")
		frappe.set_user(self.user2)
		self.assertNotIn(ref, [r["name"] for r in get_inbox_items()])


class TestLetterNumbering(CartableTestBase):
	def test_jalali_conversion(self):
		self.assertEqual(gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
		self.assertEqual(gregorian_to_jalali(2026, 11, 3), (1405, 8, 12))
		self.assertEqual(gregorian_to_jalali(2025, 3, 20), (1403, 12, 30))
		self.assertEqual(gregorian_to_jalali(2024, 2, 29), (1402, 12, 10))

	def test_number_assigned_on_registration(self):
		_set_setting("auto_letter_number", 1)
		_set_setting("letter_number_prefix", "")
		draft = self._letter(recipients=[self.user2], submit=False)
		self.assertFalse(frappe.db.get_value("Automation Letter", draft, "letter_no"))

		a = self._letter(recipients=[self.user2])
		b = self._letter(recipients=[self.user2])
		no_a = frappe.db.get_value("Automation Letter", a, "letter_no")
		no_b = frappe.db.get_value("Automation Letter", b, "letter_no")
		self.assertRegex(no_a, r"^\d{4}/\d{5}$")
		self.assertEqual(int(no_b.split("/")[1]), int(no_a.split("/")[1]) + 1)

	def test_manual_number_and_prefix(self):
		_set_setting("auto_letter_number", 1)
		_set_setting("letter_number_prefix", "م-")
		self.assertTrue(make_letter_number().startswith("م-"))

		doc = frappe.get_doc(
			{
				"doctype": "Automation Letter",
				"subject": "manual",
				"date": today(),
				"letter_no": f"MANUAL-{frappe.generate_hash(length=6)}",
			}
		).insert(ignore_permissions=True)
		doc.submit()
		self.assertTrue(doc.letter_no.startswith("MANUAL-"))

	def test_numbering_can_be_disabled(self):
		_set_setting("auto_letter_number", 0)
		letter = self._letter(recipients=[self.user2])
		self.assertFalse(frappe.db.get_value("Automation Letter", letter, "letter_no"))


class TestFoldersAndSearch(CartableTestBase):
	def test_done_folder_keeps_handled_items(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		approve_referral(ref)
		self.assertNotIn(ref, [r["name"] for r in get_inbox_items()])
		done = get_inbox_items(folder="done")
		self.assertIn(ref, [r["name"] for r in done])

	def test_inbox_rows_carry_full_names(self):
		letter = self._letter(recipients=[self.user2])
		frappe.set_user(self.user2)
		row = next(r for r in get_inbox_items() if r["reference_name"] == letter)
		self.assertEqual(row["sender_name"], frappe.utils.get_fullname(self.user1))
		self.assertIn("letter_no", row)

	def test_search_respects_permissions(self):
		token = frappe.generate_hash(length=10)
		letter = self._letter(recipients=[self.user2], subject=f"Budget {token}")

		frappe.set_user(self.user2)
		self.assertIn(letter, [r.name for r in search_letters(token)])
		letter_no = frappe.db.get_value("Automation Letter", letter, "letter_no")
		if letter_no:
			self.assertIn(letter, [r.name for r in search_letters(letter_no)])

		frappe.set_user(self.stranger)
		self.assertEqual(search_letters(token), [])
		self.assertEqual(search_letters("x"), [])  # too short

	def test_folder_counts_shape(self):
		self._letter(recipients=[self.user2])
		frappe.set_user(self.user2)
		counts = get_folder_counts()
		self.assertGreaterEqual(counts["inbox"]["all"], 1)
		self.assertIn("returned", counts["outbox"])


class TestPublicVisibility(CartableTestBase):
	def test_public_letters_hidden_by_default(self):
		_set_setting("public_letters_visible", 0)
		letter = self._letter(recipients=[self.user2])
		frappe.set_user(self.stranger)
		self.assertFalse(frappe.has_permission("Automation Letter", "read", letter))

	def test_public_letters_visible_when_enabled(self):
		_set_setting("public_letters_visible", 1)
		public = self._letter(recipients=[self.user2])
		private = self._letter(recipients=[self.user2], is_private=1)
		secret = self._letter(recipients=[self.user2], confidentiality="Secret")
		draft = self._letter(recipients=[self.user2], submit=False)

		frappe.set_user(self.stranger)
		self.assertTrue(frappe.has_permission("Automation Letter", "read", public))
		self.assertFalse(frappe.has_permission("Automation Letter", "write", public))
		for name in (private, secret, draft):
			self.assertFalse(frappe.has_permission("Automation Letter", "read", name), name)

		visible = frappe.get_list("Automation Letter", pluck="name", limit=0)
		self.assertIn(public, visible)
		self.assertNotIn(private, visible)
		self.assertNotIn(secret, visible)


class TestActions(CartableTestBase):
	def test_done_with_note_closes_letter(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		mark_referral_actioned(ref, note="filed")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "status"), "Actioned")
		self.assertIn("filed", frappe.db.get_value("Document Referral", ref, "instruction"))
		self.assertEqual(frappe.db.get_value("Automation Letter", letter, "status"), "Closed")

	def test_outcome_cannot_be_overwritten(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		approve_referral(ref)
		from office_automation.office_automation.doctype.document_referral.document_referral import (
			reject_referral,
		)

		with self.assertRaises(frappe.ValidationError):
			reject_referral(ref)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Document Referral", ref, "outcome"), "Approved")

	def test_invalid_outcome_rejected(self):
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.set_user(self.user2)
		with self.assertRaises(frappe.ValidationError):
			mark_referral_actioned(ref, outcome="Bogus")


class TestThreadPrint(CartableTestBase):
	def test_print_escapes_referral_notes(self):
		"""Legacy notes written via db_set were never sanitised: the print format
		must escape them rather than render live markup."""
		letter = self._letter(recipients=[self.user2])
		ref = self._referral(letter, self.user2)
		frappe.db.set_value("Document Referral", ref, "instruction", '<img src=x onerror="alert(1)">')
		frappe.db.set_value("Document Referral", ref, "outcome", "Returned")

		html = frappe.get_print("Automation Letter", letter, "Automation Letter Thread")
		self.assertNotIn('<img src=x onerror="alert(1)">', html)
		self.assertIn("&lt;img", html)
		self.assertIn("oa-outcome-returned", html)
		# Names and a Jalali date are rendered (this used to crash outright).
		self.assertIn(frappe.utils.get_fullname(self.user2), html)
		self.assertRegex(html, "[۰-۹]{4}/[۰-۹]{2}/[۰-۹]{2}")
