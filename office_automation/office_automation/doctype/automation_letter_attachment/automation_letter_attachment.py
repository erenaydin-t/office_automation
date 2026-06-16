# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AutomationLetterAttachment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attachment: DF.Attach | None
		external_reference_doctype: DF.Link | None
		external_reference_name: DF.DynamicLink | None
		is_archived: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		title: DF.Data | None
	# end: auto-generated types

	pass
