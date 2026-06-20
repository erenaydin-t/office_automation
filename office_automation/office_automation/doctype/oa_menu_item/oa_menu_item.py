# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OAMenuItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		icon: DF.Literal[
			"inbox",
			"send",
			"description",
			"mail",
			"folder",
			"group",
			"settings",
			"attach_file",
			"lock",
			"check_circle",
			"forward_to_inbox",
			"visibility",
			"search",
			"label",
			"bolt",
			"rule",
			"dashboard",
		]
		label: DF.Data
		link_to: DF.Data
		link_type: DF.Literal["DocType", "Page", "Report", "URL"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
