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
		date: DF.Date
		letter_no: DF.Data | None
		letter_type: DF.Link | None
		naming_series: DF.Literal["AL-.YYYY.-"]
		recipients: DF.Table[AutomationLetterRecipient]
		sender: DF.Link
		status: DF.Literal["Draft", "Registered", "In Progress", "Closed", "Cancelled"]
		subject: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.sender:
			self.sender = frappe.session.user
		if self.status == "Cancelled" and self.docstatus != 2:
			# guard against manual edits; status is system-managed
			self.status = "Draft"
		self._validate_recipients()

	def _validate_recipients(self):
		seen = set()
		for row in self.recipients:
			if row.recipient == self.sender:
				frappe.throw(_("Row #{0}: A letter cannot be sent to its own sender.").format(row.idx))
			if row.recipient in seen:
				frappe.throw(_("Row #{0}: {1} is listed more than once.").format(row.idx, row.recipient))
			seen.add(row.recipient)

	def before_submit(self):
		# When the letter is registered in the دبیرخانه it becomes immutable
		# and ready to be referred (Erja).
		self.status = "Registered"

	def on_submit(self):
		# Submitting registers the letter AND sends it to every listed recipient,
		# creating a root Document Referral (Cartable item) for each.
		self.send_to_recipients()

	def on_cancel(self):
		self.status = "Cancelled"

	def send_to_recipients(self):
		"""Create a root referral for each recipient row (the internal 'send')."""
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
			)
