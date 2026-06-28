# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from office_automation.office_automation.api.letter import (
	create_letter,
	get_letter_for_edit,
	update_letter,
)
from office_automation.office_automation.doctype.document_referral.test_document_referral import (
	ensure_oa_user,
)


class TestLetterApi(FrappeTestCase):
	def setUp(self):
		self.user1 = ensure_oa_user("test1@example.com")
		self.user2 = ensure_oa_user("test2@example.com")
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _draft(self, **over):
		payload = {
			"subject": "Draft subject",
			"body": "<p>original</p>",
			"recipients": [{"recipient": self.user1, "referral_type": "Action"}],
			"cc": [{"recipient": self.user2}],
		}
		payload.update(over)
		return create_letter(json.dumps(payload), submit=0)

	def test_update_draft_persists_changes(self):
		res = self._draft()
		name = res["name"]
		self.assertEqual(res["docstatus"], 0)

		update_letter(
			name,
			json.dumps(
				{
					"subject": "Edited subject",
					"body": "<p>edited</p>",
					"recipients": [{"recipient": self.user2, "referral_type": "Order"}],
					"cc": [],
				}
			),
			submit=0,
		)

		doc = frappe.get_doc("Automation Letter", name)
		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.subject, "Edited subject")
		self.assertEqual(doc.body, "<p>edited</p>")
		# Child tables are rebuilt, not appended to.
		self.assertEqual(len(doc.recipients), 1)
		self.assertEqual(doc.recipients[0].recipient, self.user2)
		self.assertEqual(doc.recipients[0].referral_type, "Order")
		self.assertEqual(len(doc.cc_recipients), 0)

	def test_get_letter_for_edit_returns_child_rows(self):
		name = self._draft()["name"]
		data = get_letter_for_edit(name)
		self.assertEqual(data["subject"], "Draft subject")
		self.assertEqual([r["recipient"] for r in data["recipients"]], [self.user1])
		self.assertEqual([c["recipient"] for c in data["cc"]], [self.user2])

	def test_cannot_edit_submitted_letter(self):
		name = self._draft()["name"]
		frappe.get_doc("Automation Letter", name).submit()

		with self.assertRaises(frappe.ValidationError):
			update_letter(name, json.dumps({"subject": "Too late"}), submit=0)
		with self.assertRaises(frappe.ValidationError):
			get_letter_for_edit(name)

	def test_update_can_submit_draft(self):
		name = self._draft()["name"]
		res = update_letter(
			name,
			json.dumps(
				{
					"subject": "Now sending",
					"recipients": [{"recipient": self.user1, "referral_type": "Action"}],
					"cc": [],
				}
			),
			submit=1,
		)
		self.assertEqual(res["docstatus"], 1)
		# Submitting delivers a referral to the recipient.
		self.assertTrue(
			frappe.db.exists(
				"Document Referral",
				{"reference_doctype": "Automation Letter", "reference_name": name, "recipient": self.user1},
			)
		)

	def test_new_letter_defaults_to_internal_type(self):
		"""A letter created without an explicit type falls back to «نامه داخلی»."""
		res = create_letter(json.dumps({"subject": "No type given"}), submit=0)
		self.assertEqual(
			frappe.db.get_value("Automation Letter", res["name"], "letter_type"), "نامه داخلی"
		)

	def test_explicit_letter_type_is_respected(self):
		res = create_letter(
			json.dumps({"subject": "Outgoing one", "letter_type": "نامه صادره"}), submit=0
		)
		self.assertEqual(
			frappe.db.get_value("Automation Letter", res["name"], "letter_type"), "نامه صادره"
		)

	def test_per_recipient_fields_survive_edit_round_trip(self):
		"""get_letter_for_edit exposes action_type/instruction and update_letter
		persists them, so the SPA can round-trip a draft without dropping them."""
		action_type = frappe.get_all("Action Type", limit=1, pluck="name")
		action_type = action_type[0] if action_type else None
		name = self._draft(
			recipients=[
				{
					"recipient": self.user1,
					"referral_type": "Order",
					"action_type": action_type,
					"instruction": "هامش اولیه",
				}
			]
		)["name"]

		data = get_letter_for_edit(name)
		self.assertEqual(data["recipients"][0]["referral_type"], "Order")
		self.assertEqual(data["recipients"][0]["action_type"], action_type)
		self.assertEqual(data["recipients"][0]["instruction"], "هامش اولیه")

		# Re-save sending the same per-recipient fields back (what the fixed SPA does).
		update_letter(
			name,
			json.dumps(
				{
					"subject": "Edited",
					"recipients": [
						{
							"recipient": self.user1,
							"referral_type": "Order",
							"action_type": action_type,
							"instruction": "هامش اولیه",
						}
					],
					"cc": [],
				}
			),
			submit=0,
		)
		row = frappe.get_doc("Automation Letter", name).recipients[0]
		self.assertEqual(row.referral_type, "Order")
		self.assertEqual(row.action_type, action_type)
		self.assertEqual(row.instruction, "هامش اولیه")

	def test_missing_letter_type_does_not_block_creation(self):
		"""A stale/renamed default Letter Type must not raise — it falls back to none."""
		res = create_letter(
			json.dumps({"subject": "No such type", "letter_type": "____nonexistent____"}), submit=0
		)
		self.assertFalse(frappe.db.get_value("Automation Letter", res["name"], "letter_type"))

	def test_subject_is_mandatory_on_update(self):
		name = self._draft()["name"]
		with self.assertRaises(frappe.ValidationError):
			update_letter(name, json.dumps({"subject": "  "}), submit=0)
