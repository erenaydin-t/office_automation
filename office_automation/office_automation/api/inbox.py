# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Whitelisted endpoints backing the Cartable (Inbox) SPA."""

import frappe
from frappe import _

from office_automation.office_automation.permissions.delegation import get_effective_users

OPEN_STATUSES = ("Unseen", "Seen")


def _enrich_with_reference(rows: list[dict]) -> list[dict]:
	"""Attach the referenced document's subject/title for display.

	Batches lookups per doctype to avoid N+1 queries.
	"""
	by_doctype: dict[str, set] = {}
	for row in rows:
		by_doctype.setdefault(row["reference_doctype"], set()).add(row["reference_name"])

	titles: dict[tuple, str] = {}
	for doctype, names in by_doctype.items():
		meta = frappe.get_meta(doctype)
		title_field = meta.get_title_field() if meta else "name"
		records = frappe.get_all(
			doctype,
			filters={"name": ["in", list(names)]},
			fields=["name", f"{title_field} as _title"],
			ignore_permissions=True,
		)
		for rec in records:
			titles[(doctype, rec["name"])] = rec.get("_title") or rec["name"]

	for row in rows:
		row["reference_title"] = titles.get(
			(row["reference_doctype"], row["reference_name"]), row["reference_name"]
		)
	return rows


@frappe.whitelist()
def get_inbox_items(user: str | None = None) -> list[dict]:
	"""Open inbox items (کارتابل) for the user.

	Returns ``Document Referral`` rows where the user — or any delegator they
	currently substitute for — is the *Recipient* and the status is not
	``Actioned``.
	"""
	user = user or frappe.session.user

	# A user may only fetch their own cartable (or one they are delegated into,
	# which is handled implicitly because get_effective_users resolves on the
	# *session* user, not the requested one).
	if user != frappe.session.user and user not in get_effective_users(frappe.session.user):
		frappe.throw(_("You can only access your own inbox."), frappe.PermissionError)

	recipients = get_effective_users(user) if user == frappe.session.user else [user]

	rows = frappe.get_all(
		"Document Referral",
		filters={
			"recipient": ["in", recipients],
			"status": ["in", OPEN_STATUSES],
		},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"sender",
			"recipient",
			"action_type",
			"instruction",
			"status",
			"parent_referral",
			"creation",
			"modified",
		],
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich_with_reference(rows)


@frappe.whitelist()
def get_sent_referrals(user: str | None = None) -> list[dict]:
	"""Referrals the user has sent out (Sent Referrals tab)."""
	user = user or frappe.session.user
	senders = get_effective_users(user) if user == frappe.session.user else [user]

	rows = frappe.get_all(
		"Document Referral",
		filters={"sender": ["in", senders]},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"sender",
			"recipient",
			"action_type",
			"instruction",
			"status",
			"parent_referral",
			"creation",
			"modified",
		],
		order_by="creation desc",
		ignore_permissions=True,
	)
	return _enrich_with_reference(rows)


@frappe.whitelist()
def get_inbox_counts(user: str | None = None) -> dict:
	"""Badge counts for the three tabs."""
	user = user or frappe.session.user
	recipients = get_effective_users(user)

	unread = frappe.db.count("Document Referral", {"recipient": ["in", recipients], "status": "Unseen"})
	pending = frappe.db.count("Document Referral", {"recipient": ["in", recipients], "status": "Seen"})
	sent = frappe.db.count("Document Referral", {"sender": ["in", recipients]})

	return {"unread": unread, "pending": pending, "sent": sent}
