# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
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

		amended_from: DF.Link | None
		archive_doctype: DF.Link | None
		archive_name: DF.DynamicLink | None
		attachments: DF.Table[AutomationLetterAttachment]
		body: DF.TextEditor | None
		date: DF.Date
		letter_no: DF.Data | None
		letter_type: DF.Link | None
		naming_series: DF.Literal["AL-.YYYY.-"]
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

	def before_submit(self):
		# When the letter is registered in the دبیرخانه it becomes immutable
		# and ready to be referred (Erja).
		self.status = "Registered"

	def on_cancel(self):
		self.status = "Cancelled"
