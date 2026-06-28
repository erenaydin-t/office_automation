# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AutomationLetter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from office_automation.office_automation.doctype.automation_letter_attachment.automation_letter_attachment import (
			AutomationLetterAttachment,
		)
		from office_automation.office_automation.doctype.automation_letter_recipient.automation_letter_recipient import (
			AutomationLetterRecipient,
		)

		amended_from: DF.Link | None
		archive_doctype: DF.Link | None
		archive_name: DF.DynamicLink | None
		attachments: DF.Table[AutomationLetterAttachment]
		body: DF.TextEditor | None
		cc_recipients: DF.Table[AutomationLetterRecipient]
		confidentiality: DF.Literal["Normal", "Confidential", "Secret"]
		date: DF.Date
		is_private: DF.Check
		letter_no: DF.Data | None
		letter_type: DF.Link | None
		naming_series: DF.Literal["AL-.YYYY.-"]
		recipients: DF.Table[AutomationLetterRecipient]
		sender: DF.Link
		status: DF.Literal["Draft", "Registered", "In Progress", "Closed", "Cancelled"]
		subject: DF.Data
		urgency: DF.Literal["Normal", "Urgent", "Immediate"]
	# end: auto-generated types

	def before_insert(self):
		# Apply the org's configured default letter type to new letters when none
		# was chosen. Stored as a setting (not hardcoded) so it works regardless of
		# how each site names/renames its Letter Types.
		if not self.letter_type:
			from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
				get_settings,
			)

			default_type = get_settings().default_letter_type
			if default_type and frappe.db.exists("Letter Type", default_type):
				self.letter_type = default_type

	def validate(self):
		if not self.sender:
			self.sender = frappe.session.user
		if self.status == "Cancelled" and self.docstatus != 2:
			# guard against manual edits; status is system-managed
			self.status = "Draft"
		self._validate_recipients()

	def _validate_recipients(self):
		"""No self-addressing, and a user may not appear twice across To + CC."""
		seen = set()
		for row in [*self.recipients, *self.cc_recipients]:
			if row.recipient == self.sender:
				frappe.throw(_("Row #{0}: A letter cannot be sent to its own sender.").format(row.idx))
			if row.recipient in seen:
				frappe.throw(_("{0} is listed more than once across Recipients/CC.").format(row.recipient))
			seen.add(row.recipient)

	def before_submit(self):
		# When the letter is registered in the دبیرخانه it becomes immutable
		# and ready to be referred (Erja).
		self.status = "Registered"

	def on_submit(self):
		# Submitting registers the letter AND sends it to every recipient (and CC),
		# creating a root Document Referral (Cartable item) for each.
		self.send_to_recipients()

	def on_cancel(self):
		self.status = "Cancelled"

	def send_to_recipients(self):
		"""Create a root referral for each To recipient and each CC recipient.

		CC rows always land in the recipient's Info / FYI folder and are flagged
		``is_cc`` so they never block the main workflow.
		"""
		from office_automation.office_automation.doctype.document_referral.document_referral import (
			create_referral,
		)

		for row in self.recipients:
			create_referral(
				reference_doctype=self.doctype,
				reference_name=self.name,
				recipient=row.recipient,
				sender=self.sender,
				instruction=row.instruction,
				action_type=row.action_type,
				referral_type=row.referral_type or "Action",
			)

		for row in self.cc_recipients:
			create_referral(
				reference_doctype=self.doctype,
				reference_name=self.name,
				recipient=row.recipient,
				sender=self.sender,
				instruction=row.instruction,
				action_type=row.action_type,
				referral_type="Info",
				is_cc=True,
			)
