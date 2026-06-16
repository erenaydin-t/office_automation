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

		create_todo: DF.Check
		notify_on_overdue: DF.Check
		overdue_after_days: DF.Int
		realtime_update: DF.Check
		send_email_notification: DF.Check
	# end: auto-generated types

	pass


def get_settings() -> "OfficeAutomationSettings":
	"""Cached accessor for the singleton settings."""
	return frappe.get_cached_doc("Office Automation Settings")
