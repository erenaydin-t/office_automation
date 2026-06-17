# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Delegation-aware permission layer.

A *Delegatee* with an active ``Delegation Rule`` transparently inherits the
*Delegator's* document-level access to ``Automation Letter`` and
``Document Referral`` for the duration of the rule.

Two Frappe hooks implement this:

* ``permission_query_conditions`` — narrows list/report queries to the set of
  documents the (effective) user may read, expressed as a single optimized SQL
  predicate.
* ``has_permission`` — the row-level gate for a single document.

Both share one resolver, :func:`get_effective_users`, which returns the current
user plus every delegator they currently substitute for. Results are cached for
the request so the resolver runs at most once per user per request.
"""

import frappe
from frappe.utils import today

PRIVILEGED_ROLES = {"System Manager", "Office Automation Manager", "Administrator"}


# --------------------------------------------------------------------------- #
# Resolver
# --------------------------------------------------------------------------- #
def is_privileged(user: str) -> bool:
	"""Managers and admins bypass the delegation/ownership filter entirely."""
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & PRIVILEGED_ROLES)


def get_active_delegators(user: str) -> list[str]:
	"""Delegators for whom ``user`` is an active delegatee *today*.

	Cached per request via ``frappe.cache().get_value`` with a short TTL so the
	indexed lookup is not repeated for every row in a list view.
	"""
	cache = frappe.cache()
	cache_key = f"oa_active_delegators::{user}"
	cached = cache.get_value(cache_key)
	if cached is not None:
		return cached

	delegators = frappe.get_all(
		"Delegation Rule",
		filters={
			"delegatee": user,
			"is_active": 1,
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		pluck="delegator",
		ignore_permissions=True,
	)
	# de-duplicate while preserving determinism
	delegators = sorted(set(delegators))
	cache.set_value(cache_key, delegators, expires_in_sec=300)
	return delegators


def get_effective_users(user: str | None = None) -> list[str]:
	"""The current user plus everyone they are an active delegatee for."""
	user = user or frappe.session.user
	return [user, *get_active_delegators(user)]


def _quoted_user_list(users: list[str]) -> str:
	return ", ".join(frappe.db.escape(u) for u in users)


# --------------------------------------------------------------------------- #
# permission_query_conditions hooks
# --------------------------------------------------------------------------- #
def get_permission_query_conditions(user: str | None = None) -> str:
	"""Dispatcher kept for backwards/manual use.

	Frappe calls the doctype-specific wrappers below, but exposing a single
	entry point is convenient for the console. It returns the Document Referral
	conditions by default.
	"""
	return document_referral_query_conditions(user)


def document_referral_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_privileged(user):
		return ""

	users = _quoted_user_list(get_effective_users(user))
	return f"""(
		`tabDocument Referral`.recipient in ({users})
		or `tabDocument Referral`.sender in ({users})
		or `tabDocument Referral`.owner in ({users})
	)"""


def automation_letter_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_privileged(user):
		return ""

	users = _quoted_user_list(get_effective_users(user))
	# A letter is visible when the effective user authored it, or appears on any
	# referral of it (as sender or recipient). EXISTS short-circuits and rides
	# the index on (reference_doctype, reference_name).
	return f"""(
		`tabAutomation Letter`.sender in ({users})
		or `tabAutomation Letter`.owner in ({users})
		or exists (
			select 1 from `tabDocument Referral` dr
			where dr.reference_doctype = 'Automation Letter'
			  and dr.reference_name = `tabAutomation Letter`.name
			  and (dr.recipient in ({users}) or dr.sender in ({users}))
		)
	)"""


# --------------------------------------------------------------------------- #
# has_permission hook (row-level)
# --------------------------------------------------------------------------- #
def has_permission(doc, ptype: str | None = None, user: str | None = None, **kwargs):
	"""Row-level gate.

	Returns ``True`` to allow (within the role grant), ``False`` to deny, or
	``None`` to defer to the default role-based decision. Managers/admins defer
	to roles (``None``) so they keep full access.
	"""
	user = user or frappe.session.user
	if is_privileged(user):
		return None  # let the standard role permissions apply (full access)

	# Creation/amend is governed by role permissions, not row ownership. A new
	# document has no name/owner/sender yet, so row-level checks would wrongly
	# deny it — defer to the role grant instead.
	if ptype in ("create", "amend") or not getattr(doc, "name", None):
		return None

	effective = set(get_effective_users(user))

	if doc.doctype == "Document Referral":
		if {doc.recipient, doc.sender, doc.owner} & effective:
			return True
		return False

	if doc.doctype == "Automation Letter":
		if {doc.get("sender"), doc.owner} & effective:
			return True
		# Visible if the effective user is on any referral of this letter.
		if frappe.db.exists(
			"Document Referral",
			{
				"reference_doctype": "Automation Letter",
				"reference_name": doc.name,
				"recipient": ["in", list(effective)],
			},
		):
			return True
		if frappe.db.exists(
			"Document Referral",
			{
				"reference_doctype": "Automation Letter",
				"reference_name": doc.name,
				"sender": ["in", list(effective)],
			},
		):
			return True
		return False

	return None
