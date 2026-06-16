// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Entry point for the Inbox (Cartable) Vue 3 SPA. Built by `bench build` into
// /assets/office_automation/js/inbox.bundle.<hash>.js and loaded on demand by
// the Frappe Page controller via `frappe.require("inbox.bundle.js")`.

import { createApp } from "vue";
import InboxApp from "./inbox/InboxApp.vue";

frappe.provide("office_automation.inbox");

office_automation.inbox.mount = function (el, props = {}) {
	const app = createApp(InboxApp, props);
	app.mount(el);
	return app;
};
