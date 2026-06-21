# Copyright (c) 2026, Milanpars and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkspaceRouting(FrappeTestCase):
	def test_workspace_type_is_set(self):
		"""`type` is mandatory on Workspace; a missing value breaks re-import."""
		wtype = frappe.db.get_value("Workspace", "Office Automation", "type")
		self.assertIn(wtype, ("Workspace", "Link", "URL"))

	def test_inbox_page_exists(self):
		"""The redirect target (oa_router.js) must resolve to a real Page."""
		self.assertTrue(frappe.db.exists("Page", "inbox"))

	def test_no_redirect_html_block(self):
		"""The old runtime redirect hack must not be present."""
		if frappe.db.exists("DocType", "Custom HTML Block"):
			leftover = frappe.get_all(
				"Custom HTML Block",
				or_filters=[["name", "like", "%redirect%"], ["name", "like", "%OA Inbox%"]],
				pluck="name",
			)
			self.assertEqual(leftover, [])
