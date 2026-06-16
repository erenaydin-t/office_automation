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


WORKSPACE_NAME = "Office Automation"
WORKSPACE_ICON = "file"


def after_install():
	create_custom_roles()
	seed_master_data()
	ensure_desk_workspace()
	frappe.db.commit()


def after_migrate():
	"""Runs on every `bench migrate` — keeps the desk icon present & visible."""
	ensure_desk_workspace()
	frappe.db.commit()


def ensure_desk_workspace():
	"""Guarantee the Office Automation workspace shows on the ERPNext desk.

	The workspace ships as a standard module file and is created automatically on
	migrate; this defensively unhides it and pins a valid icon so the sidebar
	entry always appears.
	"""
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		# Not yet synced (e.g. very first install ordering) — nothing to fix up.
		return

	updates = {}
	current = frappe.db.get_value("Workspace", WORKSPACE_NAME, ["is_hidden", "public", "icon"], as_dict=True)
	if current.is_hidden:
		updates["is_hidden"] = 0
	if not current.public:
		updates["public"] = 1
	if not current.icon:
		updates["icon"] = WORKSPACE_ICON

	if updates:
		for field, value in updates.items():
			frappe.db.set_value("Workspace", WORKSPACE_NAME, field, value)
		frappe.clear_cache()


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
