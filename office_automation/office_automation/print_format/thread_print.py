# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Thread-printing helpers.

``get_letter_thread`` assembles a single structured dictionary containing the
main letter plus its full referral (Erja) tree, flattened into a chronological
list of margin notes (توضیحات ارجاع). It is registered as a Jinja method in
``hooks.py`` so the print format can call it directly, and is also whitelisted
for ad-hoc/API use.

The output is plain JSON-serialisable data (dicts, lists, strings, datetimes),
which keeps it fully compatible with ``frappe.utils.pdf.get_pdf`` — the HTML is
rendered server-side by Jinja and handed to wkhtmltopdf without any client-side
dependencies.
"""

import frappe


def _fetch_referrals(doc_type: str, doc_name: str) -> list[dict]:
	return frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": doc_type, "reference_name": doc_name},
		fields=[
			"name",
			"parent_referral",
			"sender",
			"recipient",
			"action_type",
			"instruction",
			"status",
			"outcome",
			"is_cc",
			"referral_type",
			"seen_on",
			"actioned_on",
			"creation",
		],
		order_by="creation asc",
		ignore_permissions=True,
	)


def _build_tree(rows: list[dict]) -> list[dict]:
	nodes = {r["name"]: {**r, "children": []} for r in rows}
	roots = []
	for r in rows:
		node = nodes[r["name"]]
		parent = r.get("parent_referral")
		if parent and parent in nodes:
			nodes[parent]["children"].append(node)
		else:
			roots.append(node)
	return roots


def _flatten(nodes: list[dict], depth: int = 0, acc: list[dict] | None = None) -> list[dict]:
	"""Depth-first flatten preserving chronological order within each branch."""
	if acc is None:
		acc = []
	for node in nodes:
		acc.append({**{k: v for k, v in node.items() if k != "children"}, "depth": depth})
		_flatten(node["children"], depth + 1, acc)
	return acc


def get_letter_thread(doc_name: str) -> dict:
	"""Return ``{letter, tree, referrals}`` for an Automation Letter.

	* ``letter``     — the Automation Letter document.
	* ``tree``       — nested referral tree (each node has ``children``).
	* ``referrals``  — flat, chronological list with a ``depth`` key for
	                   indentation of margin notes in the print format.
	"""
	letter = frappe.get_doc("Automation Letter", doc_name)
	letter.check_permission("read")

	rows = _fetch_referrals("Automation Letter", doc_name)
	# Resolve display values here: Frappe's sandboxed Jinja does not expose
	# ``frappe.utils.get_fullname`` (calling it crashed the whole print), and
	# Jalali dates are rendered without needing the optional persian_calendar.
	names = _full_names({letter.sender} | {r.sender for r in rows} | {r.recipient for r in rows})
	for r in rows:
		r["sender_name"] = names.get(r.sender) or r.sender
		r["recipient_name"] = names.get(r.recipient) or r.recipient
		r["creation_fa"] = jalali_str(r.creation, with_time=True)
		r["actioned_on_fa"] = jalali_str(r.actioned_on, with_time=True) if r.actioned_on else ""
	tree = _build_tree(rows)
	referrals = _flatten(tree)

	return {
		"letter": letter,
		"sender_name": names.get(letter.sender) or letter.sender,
		"date_fa": jalali_str(letter.date),
		"tree": tree,
		"referrals": referrals,
	}


FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def jalali_str(value, with_time: bool = False) -> str:
	"""Format a date/datetime as a Jalali string with Persian digits,
	e.g. ``۱۴۰۵/۰۸/۱۲`` or ``۱۴۰۵/۰۸/۱۲ ۱۴:۳۰``."""
	from office_automation.office_automation.doctype.automation_letter.automation_letter import (
		gregorian_to_jalali,
	)

	if not value:
		return ""
	dt = frappe.utils.get_datetime(value)
	jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
	out = f"{jy}/{jm:02d}/{jd:02d}"
	if with_time:
		out += f" {dt.hour:02d}:{dt.minute:02d}"
	return out.translate(FA_DIGITS)


def _full_names(users: set) -> dict:
	users = [u for u in users if u]
	if not users:
		return {}
	rows = frappe.get_all(
		"User", filters={"name": ["in", users]}, fields=["name", "full_name"], ignore_permissions=True
	)
	return {r.name: r.full_name for r in rows}


@frappe.whitelist()
def get_letter_thread_api(doc_name: str) -> dict:
	"""Whitelisted wrapper returning JSON-safe data (without the doc object)."""
	thread = get_letter_thread(doc_name)
	letter = thread["letter"]
	return {
		"letter": {
			"name": letter.name,
			"subject": letter.subject,
			"letter_no": letter.letter_no,
			"date": letter.date,
			"sender": letter.sender,
			"sender_name": thread["sender_name"],
			"date_fa": thread["date_fa"],
			"body": letter.body,
			"status": letter.status,
		},
		"referrals": thread["referrals"],
	}
