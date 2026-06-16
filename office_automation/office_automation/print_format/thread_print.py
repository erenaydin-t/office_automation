# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt
"""Thread-printing helpers.

``get_letter_thread`` assembles a single structured dictionary containing the
main letter plus its full referral (Erja) tree, flattened into a chronological
list of margin notes (هامش‌نویسی). It is registered as a Jinja method in
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
	tree = _build_tree(rows)
	referrals = _flatten(tree)

	return {"letter": letter, "tree": tree, "referrals": referrals}


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
			"body": letter.body,
			"status": letter.status,
		},
		"referrals": thread["referrals"],
	}
