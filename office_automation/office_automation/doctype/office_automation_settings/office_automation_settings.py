# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OfficeAutomationSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_letter_number: DF.Check
		create_todo: DF.Check
		default_letter_type: DF.Link | None
		letter_number_prefix: DF.Data | None
		notify_on_overdue: DF.Check
		overdue_after_days: DF.Int
		public_letters_visible: DF.Check
		realtime_update: DF.Check
		send_email_notification: DF.Check
	# end: auto-generated types

	def validate(self):
		if (self.overdue_after_days or 0) < 0:
			self.overdue_after_days = 0

	def on_update(self):
		# Visibility rules are evaluated inside permission hooks; make sure no
		# stale cached copy of the singleton keeps the old behaviour.
		frappe.clear_document_cache(self.doctype, self.doctype)


def get_settings() -> "OfficeAutomationSettings":
	"""Cached accessor for the singleton settings."""
	return frappe.get_cached_doc("Office Automation Settings")
