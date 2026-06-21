// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Routing-layer guard: when the user opens the "Office Automation" workspace,
// send them to the Inbox page instead. This runs via frappe.router's change
// event (the correct layer) so the navigation is NOT swallowed by the
// workspace's own render — unlike a redirect inside a Custom HTML Block.
//
// The workspace content page (Correspondence / Masters / Access Control cards)
// stays reachable for admins via `?noredirect=1`.

frappe.provide("office_automation");

office_automation.WORKSPACE_SLUGS = ["office-automation", "office automation"];

office_automation.route_guard = function () {
	try {
		const route = (frappe.get_route && frappe.get_route()) || [];

		// A workspace route is a single segment (the workspace slug/name).
		const first = String(route[0] || "").toLowerCase();
		const isWorkspace = route.length <= 1 && office_automation.WORKSPACE_SLUGS.includes(first);
		if (!isWorkspace) return;

		const noredirect =
			(frappe.utils && frappe.utils.get_url_arg && frappe.utils.get_url_arg("noredirect") === "1") ||
			/[?&]noredirect=1\b/.test(window.location.search);
		if (noredirect) return;

		frappe.set_route("inbox");
	} catch (e) {
		/* never break desk routing */
	}
};

$(() => {
	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", office_automation.route_guard);
	}
	// Handle a direct/deep load onto the workspace.
	setTimeout(office_automation.route_guard, 300);
});
