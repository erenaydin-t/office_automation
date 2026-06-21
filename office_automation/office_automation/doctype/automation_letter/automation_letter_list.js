// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt
//
// Office Automation template look for the Automation Letter LIST page.
// Self-contained: the list script loads without the form script.

(function () {
	function injectStyle() {
		if (document.getElementById("oa-template-style")) return;
		const css = `
@import url("https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap");
.oa-form, .oa-list { font-family: "Vazirmatn", var(--font-stack, sans-serif); }

.oa-form .form-page .form-section {
	background: var(--card-bg, #ffffff);
	border: 1px solid var(--border-color, #e7ecf3);
	border-radius: 14px;
	box-shadow: 0 1px 2px rgba(20,30,60,.06), 0 1px 3px rgba(20,30,60,.05);
	padding: 8px 18px 12px;
	margin: 0 0 16px;
	transition: box-shadow .15s ease;
}
.oa-form .form-page .form-section:hover {
	box-shadow: 0 4px 12px rgba(20,30,60,.08), 0 2px 6px rgba(20,30,60,.05);
}
.oa-form .form-section .section-head { font-weight: 600; color: var(--heading-color, #1a1c22); letter-spacing: -.01em; }
.oa-form .control-label { font-weight: 500; color: var(--text-muted); }
.oa-form .form-control, .oa-form .input-with-feedback,
.oa-form .like-disabled-input, .oa-form .ql-container, .oa-form .ql-toolbar { border-radius: 9px; }
.oa-form .form-grid { border-radius: 10px; overflow: hidden; }

.oa-form .page-title .title-text, .oa-list .page-title .title-text { font-weight: 700; letter-spacing: -.01em; }
.oa-form .btn, .oa-list .btn { border-radius: 9px; }
.oa-form .btn-primary, .oa-list .btn-primary { background: #1a56db; border-color: #1a56db; }
.oa-form .btn-primary:hover, .oa-list .btn-primary:hover { background: #1342b0; border-color: #1342b0; }
.oa-form .indicator-pill, .oa-list .indicator-pill { border-radius: 20px; }

.oa-list .result { border-radius: 14px; overflow: hidden; }
.oa-list .list-row:hover { background: var(--fg-hover-color, var(--control-bg)); }
`;
		const el = document.createElement("style");
		el.id = "oa-template-style";
		el.textContent = css;
		document.head.appendChild(el);
	}

	frappe.listview_settings["Automation Letter"] = {
		onload(listview) {
			injectStyle();
			const wrapper = listview && listview.page && listview.page.wrapper;
			if (wrapper) wrapper.classList.add("oa-list");
		},
	};
})();
