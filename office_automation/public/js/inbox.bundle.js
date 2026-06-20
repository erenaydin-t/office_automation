// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Entry point for the Cartable (Inbox) Vue 3 SPA. It mounts INSIDE the Frappe
// page content area (it does not cover the ERPNext navbar/sidebar) so it stays
// in sync with the desk chrome, theme and RTL/LTR direction.

import { createApp } from "vue";
import InboxApp from "./inbox/InboxApp.vue";
import "./inbox/theme.css";

frappe.provide("office_automation.inbox");

office_automation.inbox.mount = function (el, props = {}) {
	const app = createApp(InboxApp, props);
	app.mount(el);
	return app;
};
