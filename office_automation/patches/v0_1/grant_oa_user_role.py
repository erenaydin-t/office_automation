# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Grant the Office Automation User role to all active staff (one-time).

Makes the app usable out of the box: every enabled System User can create and
receive letters via the Cartable. Remove the role from individual users
afterwards if you want to restrict access.
"""

import frappe

ROLE = "Office Automation User"


def execute():
	if not frappe.db.exists("Role", ROLE):
		return

	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		pluck="name",
	)
	for user in users:
		if user in ("Administrator", "Guest"):
			continue
		if frappe.db.exists("Has Role", {"parent": user, "role": ROLE}):
			continue
		try:
			frappe.get_doc("User", user).add_roles(ROLE)
		except Exception:
			frappe.log_error(title=f"office_automation: could not grant role to {user}")

	frappe.db.commit()
