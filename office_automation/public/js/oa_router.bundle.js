// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Routing-layer guard: when the user opens the "Office Automation" workspace,
// send them to the Inbox page instead. This runs via frappe.router's change
// event (the correct layer) so the navigation is NOT swallowed by the
// workspace's own render — unlike a redirect inside a Custom HTML Block.
//
// Built as a `.bundle.js` (not a plain asset) so Frappe reliably includes it
// via `app_include_js` and content-hashes it — the browser can never serve a
// stale copy that silently skips the redirect.
//
// The workspace content page (Correspondence / Masters / Access Control cards)
// stays reachable for admins via `?noredirect=1`.

frappe.provide("office_automation");

office_automation.WORKSPACE_SLUGS = ["office-automation", "office automation"];

office_automation.route_guard = function () {
	try {
		const route = (frappe.get_route && frappe.get_route()) || [];

		// A workspace route is a single segment (the slug), or the two-segment
		// ["Workspaces", "<slug>"] shape some versions/deep-links produce.
		const segments = route.map((s) => String(s || "").toLowerCase());
		const hit = segments.some((s) => office_automation.WORKSPACE_SLUGS.includes(s));
		const isWorkspace = hit && route.length <= 2;
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

	// Catch a direct/deep full-page load onto the workspace, where no router
	// "change" event fires. frappe.get_route() isn't populated synchronously on
	// boot, so poll briefly instead of relying on a single fixed timer.
	let tries = 0;
	const kick = () => {
		const ready = frappe.get_route && (frappe.get_route() || []).length;
		if (ready) {
			office_automation.route_guard();
			return;
		}
		if (tries++ < 20) setTimeout(kick, 100); // up to ~2s
	};
	kick();
});
