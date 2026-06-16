# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Helpers for the apps-screen entry."""

import frappe

APP_ROLES = {"System Manager", "Office Automation Manager", "Office Automation User"}


def has_app_permission(user: str | None = None) -> bool:
	"""Show the Office Automation app icon only to users with a relevant role."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & APP_ROLES)
