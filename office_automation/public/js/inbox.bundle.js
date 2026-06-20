// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Entry point for the Office Automation Panel (Cartable) Vue 3 SPA. It mounts
// INSIDE the Frappe page content area — it no longer covers the ERPNext navbar
// or sidebar — and follows the desk theme (light/dark) and RTL/LTR direction.

import { createApp } from "vue";
import OaPanel from "./inbox/OaPanel.vue";
import "./inbox/theme.css";
import "./inbox/panel.css";

frappe.provide("office_automation.inbox");

office_automation.inbox.mount = function (el, props = {}) {
	const app = createApp(OaPanel, props);
	app.mount(el);
	return app;
};
