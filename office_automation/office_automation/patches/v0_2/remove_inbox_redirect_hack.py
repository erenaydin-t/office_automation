# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Remove the old runtime inbox-redirect hack from existing sites.

Earlier the workspace was redirected to the inbox by injecting a Custom HTML
Block ("OA Inbox Redirect") into the workspace at runtime via the UI/API. That
artifact lived only in the DB (never in code). The redirect is now handled at
the routing layer (oa_router.js), so this patch deterministically removes the
old artifacts. Idempotent: safe to run repeatedly / on sites that never had it.
"""

import json

import frappe

WORKSPACE = "Office Automation"


def execute():
	_delete_redirect_html_blocks()
	_strip_redirect_from_workspace()
	frappe.db.commit()


def _delete_redirect_html_blocks():
	if not frappe.db.exists("DocType", "Custom HTML Block"):
		return
	names = frappe.get_all(
		"Custom HTML Block",
		or_filters=[
			["name", "like", "%redirect%"],
			["name", "like", "%OA Inbox%"],
		],
		pluck="name",
	)
	for name in names:
		frappe.delete_doc("Custom HTML Block", name, ignore_permissions=True, force=True)


def _strip_redirect_from_workspace():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	changed = False

	# Remove any content block that references the redirect.
	try:
		blocks = json.loads(ws.content or "[]")
		kept = [b for b in blocks if "redirect" not in json.dumps(b).lower()]
		if len(kept) != len(blocks):
			ws.content = json.dumps(kept)
			changed = True
	except Exception:
		pass

	# Remove custom-block child rows referencing the redirect.
	if ws.get("custom_blocks"):
		kept_rows = [
			b for b in ws.custom_blocks if "redirect" not in (b.get("custom_block_name") or "").lower()
		]
		if len(kept_rows) != len(ws.custom_blocks):
			ws.custom_blocks = kept_rows
			changed = True

	if changed:
		ws.save(ignore_permissions=True)
