# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return {
		"fieldname": "reference_name",
		"non_standard_fieldnames": {
			"Document Referral": "reference_name",
		},
		"transactions": [
			{
				"label": _("Routing"),
				"items": ["Document Referral"],
			},
		],
	}
