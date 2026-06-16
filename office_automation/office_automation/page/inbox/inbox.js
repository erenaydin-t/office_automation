// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt

frappe.pages["inbox"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Inbox / کارتابل"),
		single_column: true,
	});

	// Mount point for the Vue 3 SPA.
	const $container = $('<div class="oa-inbox-root"></div>').appendTo(page.main);

	// The Vue app is built as a bundle so it can use SFCs + the Vue runtime.
	frappe.require("inbox.bundle.js").then(() => {
		// office_automation.inbox.mount is registered by the bundle.
		wrapper.__oa_inbox_app = office_automation.inbox.mount($container.get(0), { page });
	});

	// Tear down the Vue app when navigating away to avoid leaks.
	$(wrapper).on("remove", () => {
		if (wrapper.__oa_inbox_app) {
			wrapper.__oa_inbox_app.unmount();
			wrapper.__oa_inbox_app = null;
		}
	});
};
