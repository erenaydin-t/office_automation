# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Install-time setup for Office Automation."""

import frappe

CUSTOM_ROLES = [
	{
		"role_name": "Office Automation Manager",
		"desk_access": 1,
		"description": "Full control over letters, referrals and delegation rules.",
	},
	{
		"role_name": "Office Automation User",
		"desk_access": 1,
		"description": "Creates and receives letters via the Cartable (inbox).",
	},
]


DEFAULT_LETTER_TYPES = [
	("Incoming", "نامه وارده"),
	("Outgoing", "نامه صادره"),
	("Internal", "نامه داخلی"),
	("Circular", "بخشنامه"),
]

DEFAULT_ACTION_TYPES = [
	("For Review", "جهت بررسی"),
	("For Action", "جهت اقدام"),
	("For Information", "جهت اطلاع"),
	("For Approval", "جهت تأیید"),
	("Please Follow Up", "پیگیری شود"),
	("Archive", "بایگانی شود"),
]


def after_install():
	create_custom_roles()
	seed_master_data()
	frappe.db.commit()


def seed_master_data():
	for name, description in DEFAULT_LETTER_TYPES:
		if not frappe.db.exists("Letter Type", name):
			frappe.get_doc(
				{"doctype": "Letter Type", "letter_type_name": name, "description": description}
			).insert(ignore_permissions=True)

	for name, description in DEFAULT_ACTION_TYPES:
		if not frappe.db.exists("Action Type", name):
			frappe.get_doc(
				{"doctype": "Action Type", "action_type_name": name, "description": description}
			).insert(ignore_permissions=True)


def create_custom_roles():
	for role in CUSTOM_ROLES:
		if frappe.db.exists("Role", role["role_name"]):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role["role_name"],
				"desk_access": role["desk_access"],
				"home_page": "/app/inbox",
			}
		)
		doc.insert(ignore_permissions=True)
