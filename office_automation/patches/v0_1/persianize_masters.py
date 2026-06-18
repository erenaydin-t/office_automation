# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Rename the default English Letter/Action types to Persian on existing sites.

`frappe.rename_doc` updates every link (Automation Letter.letter_type,
Document Referral.action_type, child rows) automatically. If the Persian target
already exists, the old record is merged into it.
"""

import frappe

LETTER_TYPE_MAP = {
	"Incoming": "نامه وارده",
	"Outgoing": "نامه صادره",
	"Internal": "نامه داخلی",
	"Circular": "بخشنامه",
}

ACTION_TYPE_MAP = {
	"For Review": "جهت بررسی",
	"For Action": "جهت اقدام",
	"For Information": "جهت اطلاع",
	"For Approval": "جهت تأیید",
	"Please Follow Up": "پیگیری شود",
	"Archive": "بایگانی شود",
}


def _rename_all(doctype: str, mapping: dict):
	for old, new in mapping.items():
		if not frappe.db.exists(doctype, old):
			continue
		if old == new:
			continue
		merge = bool(frappe.db.exists(doctype, new))
		# Patches run as Administrator; rename_doc updates all links automatically.
		# (v16 rename_doc no longer accepts ignore_permissions; the masters set
		# allow_rename so no `force` is required.)
		frappe.rename_doc(doctype, old, new, merge=merge)


def execute():
	_rename_all("Letter Type", LETTER_TYPE_MAP)
	_rename_all("Action Type", ACTION_TYPE_MAP)
	frappe.db.commit()
