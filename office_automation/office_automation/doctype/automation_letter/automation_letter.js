// Copyright (c) 2026, Milanpars and contributors
// For license information, please see license.txt

frappe.ui.form.on("Automation Letter", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			// Draft: help the user send the letter to employees on submit.
			frm.add_custom_button(__("Add Recipient"), () =>
				office_automation_add_recipient_dialog(frm)
			);

			// "Submit & Refer" — submit (which sends to recipients) then open the
			// Erja dialog to route it onward immediately.
			if (!frm.is_new()) {
				frm.add_custom_button(__("Submit & Refer"), () => {
					frm.savesubmit().then(() => office_automation_forward_dialog(frm));
				});
			}

			if (!(frm.doc.recipients || []).length) {
				frm.dashboard.set_headline(
					__(
						"Add one or more recipients below, then <b>Submit</b> to send this letter to their Cartable."
					)
				);
			}
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Forward (Erja)"),
				() => office_automation_forward_dialog(frm),
				__("Actions")
			);

			frm.add_custom_button(
				__("View Referral Tree"),
				() => office_automation_show_tree(frm),
				__("Actions")
			);
		}
	},
});

function office_automation_add_recipient_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Add Recipient"),
		fields: [
			{
				label: __("Recipient (Employee)"),
				fieldname: "recipient",
				fieldtype: "Link",
				options: "User",
				reqd: 1,
			},
			{
				label: __("Action Type"),
				fieldname: "action_type",
				fieldtype: "Link",
				options: "Action Type",
			},
			{
				label: __("Instruction (هامش‌نویسی)"),
				fieldname: "instruction",
				fieldtype: "Small Text",
			},
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			const exists = (frm.doc.recipients || []).some((r) => r.recipient === values.recipient);
			if (exists) {
				frappe.msgprint(__("{0} is already a recipient.", [values.recipient]));
				return;
			}
			const row = frm.add_child("recipients", {
				recipient: values.recipient,
				action_type: values.action_type,
				instruction: values.instruction,
			});
			frm.refresh_field("recipients");
			frm.dashboard.clear_headline();
			frappe.show_alert({
				message: __("Recipient added — Submit to send."),
				indicator: "blue",
			});
			d.hide();
			return row;
		},
	});
	d.show();
}

function office_automation_forward_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Forward Letter (Erja)"),
		fields: [
			{
				label: __("Recipient"),
				fieldname: "recipient",
				fieldtype: "Link",
				options: "User",
				reqd: 1,
			},
			{
				label: __("Referral Type"),
				fieldname: "referral_type",
				fieldtype: "Select",
				options: "Order\nFollow-up\nAction\nNotification\nInfo",
				default: "Action",
			},
			{
				label: __("Action Type"),
				fieldname: "action_type",
				fieldtype: "Link",
				options: "Action Type",
			},
			{
				label: __("Instruction / Note (هامش‌نویسی)"),
				fieldname: "instruction",
				fieldtype: "Small Text",
			},
			{
				label: __("Parent Referral"),
				fieldname: "parent_referral",
				fieldtype: "Link",
				options: "Document Referral",
				description: __("Leave blank to refer directly from the letter."),
			},
		],
		primary_action_label: __("Forward"),
		primary_action(values) {
			frappe.call({
				method: "office_automation.office_automation.doctype.document_referral.document_referral.forward_document",
				args: {
					doc_type: frm.doctype,
					doc_name: frm.docname,
					recipient: values.recipient,
					referral_type: values.referral_type,
					instruction: values.instruction,
					action_type: values.action_type,
					parent_referral: values.parent_referral,
				},
				freeze: true,
				freeze_message: __("Forwarding..."),
				callback() {
					frappe.show_alert({
						message: __("Letter forwarded to {0}", [values.recipient]),
						indicator: "green",
					});
					d.hide();
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}

function office_automation_show_tree(frm) {
	frappe.call({
		method: "office_automation.office_automation.doctype.document_referral.document_referral.get_referral_tree",
		args: { doc_type: frm.doctype, doc_name: frm.docname },
		callback(r) {
			const tree = r.message || [];
			const html = office_automation_render_tree(tree);
			const d = new frappe.ui.Dialog({
				title: __("Referral Tree (درخت ارجاعات)"),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "tree", options: html }],
			});
			d.show();
		},
	});
}

function office_automation_render_tree(nodes, depth = 0) {
	if (!nodes || !nodes.length) {
		return depth === 0 ? `<p class="text-muted">${__("No referrals yet.")}</p>` : "";
	}
	let html = `<ul style="list-style:none;padding-left:${depth ? 20 : 0}px">`;
	for (const node of nodes) {
		html += `<li style="margin:6px 0">
			<b>${frappe.utils.escape_html(node.sender || "")}</b>
			→ <b>${frappe.utils.escape_html(node.recipient || "")}</b>
			<span class="indicator-pill ${office_automation_status_color(node.status)}">${frappe.utils.escape_html(node.status || "")}</span>
			<div class="text-muted small">${frappe.utils.escape_html(node.instruction || "")}</div>
			${office_automation_render_tree(node.children, depth + 1)}
		</li>`;
	}
	html += "</ul>";
	return html;
}

function office_automation_status_color(status) {
	return (
		{
			Draft: "gray",
			Unseen: "orange",
			Seen: "blue",
			Actioned: "green",
		}[status] || "gray"
	);
}
