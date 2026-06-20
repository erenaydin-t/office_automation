// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Tags this app's desk form/list pages with `.oa-form` / `.oa-list` so the
// scoped theme in oa_forms.css applies — and nothing else in ERPNext is touched.

frappe.provide("office_automation");

office_automation.THEME_DOCTYPES = [
	"Automation Letter",
	"Document Referral",
	"Delegation Rule",
	"Letter Type",
	"Action Type",
	"Office Automation Settings",
	"OA Menu Item",
];

office_automation.apply_theme = function () {
	try {
		const route = (frappe.get_route && frappe.get_route()) || [];
		const view = route[0];
		const dt = route[1];
		const ours = office_automation.THEME_DOCTYPES.includes(dt);

		if (view === "Form" && window.cur_frm && cur_frm.page && cur_frm.page.wrapper) {
			cur_frm.page.wrapper.classList.toggle("oa-form", ours && cur_frm.doctype === dt);
		} else if (view === "List" && window.cur_list && cur_list.page && cur_list.page.wrapper) {
			cur_list.page.wrapper.classList.toggle("oa-list", ours);
		}
	} catch (e) {
		/* never break the desk */
	}
};

$(() => {
	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", () => setTimeout(office_automation.apply_theme, 80));
	}
	// Initial / deep-link load.
	setTimeout(office_automation.apply_theme, 400);
});
