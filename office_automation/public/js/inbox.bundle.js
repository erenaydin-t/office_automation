// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Entry point for the Office Automation Panel (Cartable) Vue 3 SPA. Built by
// `bench build` into /assets/office_automation/js/inbox.bundle.<hash>.js and
// loaded on demand by the Frappe Page controller.

import { createApp } from "vue";
import OaPanel from "./inbox/OaPanel.vue";
import "./inbox/theme.css";
import "./inbox/panel.css";
import "./inbox/oa_fonts.css";

frappe.provide("office_automation.inbox");

office_automation.inbox.mount = function (el, props = {}) {
	const app = createApp(OaPanel, props);
	app.mount(el);
	return app;
};
