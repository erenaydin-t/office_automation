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


# (Persian name, English note)
DEFAULT_LETTER_TYPES = [
	("نامه وارده", "Incoming"),
	("نامه صادره", "Outgoing"),
	("نامه داخلی", "Internal"),
	("بخشنامه", "Circular"),
]

DEFAULT_ACTION_TYPES = [
	("جهت بررسی", "For Review"),
	("جهت اقدام", "For Action"),
	("جهت اطلاع", "For Information"),
	("جهت تأیید", "For Approval"),
	("پیگیری شود", "Please Follow Up"),
	("بایگانی شود", "Archive"),
]


WORKSPACE_NAME = "Office Automation"
WORKSPACE_ICON = "file"

# Global default flag marking that the one-time Jalali auto-enable has run, so
# later migrations respect an admin who deliberately switched it back off.
JALALI_INIT_FLAG = "office_automation_jalali_initialized"


def after_install():
	create_custom_roles()
	seed_master_data()
	ensure_desk_workspace()
	enable_jalali_calendar()
	ensure_default_letter_type()
	frappe.db.commit()


def after_migrate():
	"""Runs on every `bench migrate` — keeps the desk icon present & visible."""
	ensure_desk_workspace()
	enable_jalali_calendar()
	ensure_default_letter_type()
	frappe.db.commit()


def ensure_default_letter_type():
	"""Default new letters to the seeded Internal type «نامه داخلی», once.

	Only sets it when the setting is blank and that type exists, so it never
	overrides an admin's choice — and sites that renamed their types (e.g.
	«1-نامه داخلی») simply pick their own value in Office Automation Settings.
	"""
	if not frappe.db.exists("DocType", "Office Automation Settings"):
		return
	if frappe.db.get_single_value("Office Automation Settings", "default_letter_type"):
		return
	internal = "نامه داخلی"
	if frappe.db.exists("Letter Type", internal):
		frappe.db.set_single_value("Office Automation Settings", "default_letter_type", internal)


def enable_jalali_calendar():
	"""Turn on Jalali display by default for Persian deployments — once.

	When the optional ``persian_calendar`` app is installed, its **Jalali
	Settings** singleton exists by the time we run. On the *first* pass we enable
	it (Default Calendar = Jalali) and record a global flag. After that the flag
	makes us a no-op, so an admin who later switches it off (or tweaks week
	start/end) is respected on subsequent migrations. Best-effort: never block
	migrate if the app is absent or its schema changes.
	"""
	if frappe.db.get_default(JALALI_INIT_FLAG):
		return
	if not frappe.db.exists("DocType", "Jalali Settings"):
		# Required app not migrated yet — retry on the next migrate (no flag set).
		return
	try:
		# Don't override a value the admin already set; only enable when still off.
		if not frappe.db.get_single_value("Jalali Settings", "enable_jalali"):
			frappe.db.set_single_value("Jalali Settings", "enable_jalali", 1)
			frappe.db.set_single_value("Jalali Settings", "default_calendar", "Jalali")
		# Mark the one-time pass done (whether we enabled it or it was already on).
		frappe.db.set_default(JALALI_INIT_FLAG, "1")
	except Exception:
		frappe.log_error(title="office_automation: enabling Jalali calendar failed")


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
