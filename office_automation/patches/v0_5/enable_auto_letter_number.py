# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Turn on secretariat auto-numbering for sites upgraded from < v0.5.

New Check fields on a Single DocType have no stored row on existing sites, so
they read as 0 instead of their declared default. Seed the defaults once —
only where no value exists yet, so an admin's explicit choice is never touched.
"""

import frappe

DOCTYPE = "Office Automation Settings"
DEFAULTS = {"auto_letter_number": 1, "public_letters_visible": 0}


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	for field, value in DEFAULTS.items():
		exists = frappe.db.sql(
			"select 1 from `tabSingles` where doctype=%s and field=%s",
			(DOCTYPE, field),
		)
		if not exists:
			frappe.db.set_single_value(DOCTYPE, field, value)
	frappe.clear_document_cache(DOCTYPE, DOCTYPE)
