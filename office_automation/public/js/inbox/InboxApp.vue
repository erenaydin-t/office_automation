<template>
	<div class="oa-cartable oa-ui">
		<!-- ---------------- Sidebar ---------------- -->
		<aside class="oa-sidebar">
			<button class="oa-btn oa-btn-primary oa-new-btn" @click="createLetter">
				<OaIcon name="plus" :size="16" /> {{ __("ایجاد نامه جدید") }}
			</button>

			<template v-for="node in folders" :key="node.key">
				<div v-if="node.group" class="oa-group-title">{{ node.label }}</div>
				<a
					v-else
					href="#"
					class="oa-folder"
					:class="{ active: activeFolder === node.key, child: node.child }"
					@click.prevent="selectFolder(node)"
				>
					<span class="oa-folder-label">
						<OaIcon v-if="!node.child" :name="folderIcon(node)" :size="16" />
						{{ node.label }}
					</span>
					<span v-if="badge(node) != null" class="oa-count">{{ badge(node) }}</span>
				</a>
			</template>
		</aside>

		<!-- ---------------- Main panel ---------------- -->
		<section class="oa-main">
			<div class="oa-main-head">
				<h4 class="oa-title">{{ activeLabel }}</h4>
				<div class="oa-tools">
					<input
						ref="search"
						v-model="search"
						type="text"
						class="form-control oa-search"
						:placeholder="__('جستجو: موضوع، دستور، فرستنده…')"
					/>
					<select v-model="urgencyFilter" class="form-control oa-mini">
						<option value="">{{ __("همه فوریت‌ها") }}</option>
						<option value="Immediate">{{ __("آنی") }}</option>
						<option value="Urgent">{{ __("فوری") }}</option>
						<option value="Normal">{{ __("عادی") }}</option>
					</select>
					<button class="btn btn-default btn-sm" @click="refresh" :disabled="loading">
						{{ loading ? __("…") : __("تازه‌سازی") }}
					</button>
				</div>
			</div>

			<div v-if="loading" class="oa-empty text-muted">{{ __("در حال بارگذاری…") }}</div>
			<div v-else-if="!filteredItems.length" class="oa-empty text-muted">
				{{ __("موردی یافت نشد.") }}
			</div>

			<div v-else class="oa-list">
				<div
					v-for="item in filteredItems"
					:key="item.name"
					class="oa-card"
					:class="cardClass(item)"
					@click="openItem(item)"
				>
					<div class="oa-card-head">
						<span class="oa-subject">{{ item.title }}</span>
						<span class="oa-badges">
							<span v-if="item.urgency && item.urgency !== 'Normal'" class="pill urgent">
								{{ faUrgency(item.urgency) }}
							</span>
							<span
								v-if="item.confidentiality && item.confidentiality !== 'Normal'"
								class="pill conf"
							>
								{{ faConf(item.confidentiality) }}
							</span>
							<span v-if="item.is_cc" class="pill cc">{{ __("رونوشت") }}</span>
							<span class="pill" :class="statusColor(item)">{{ item.statusLabel }}</span>
						</span>
					</div>
					<div class="oa-meta text-muted">
						<span v-if="item.kind === 'referral'">
							<template v-if="scope === 'outbox'">→ {{ item.recipient }}</template>
							<template v-else>{{ __("از") }} {{ item.sender }}</template>
							<span v-if="item.referral_type"> · {{ faType(item.referral_type) }}</span>
						</span>
						<span v-else>{{ item.subtitle }}</span>
						<span class="oa-time">{{ prettyTime(item.creation || item.modified) }}</span>
					</div>
					<div v-if="item.instruction" class="oa-instruction">{{ item.instruction }}</div>

					<div class="oa-actions" v-if="item.kind === 'referral' && scope === 'inbox'">
						<button class="btn btn-xs btn-primary" @click.stop="openReference(item)">
							{{ __("بازکردن") }}
						</button>
						<button class="btn btn-xs btn-default" @click.stop="forward(item)">
							{{ __("ارجاع") }}
						</button>
						<template v-if="needsDecision(item)">
							<button class="btn btn-xs btn-success" @click.stop="decide(item, 'approve')">
								{{ __("تأیید") }}
							</button>
							<button class="btn btn-xs btn-danger" @click.stop="decide(item, 'reject')">
								{{ __("رد") }}
							</button>
						</template>
						<button v-else class="btn btn-xs btn-success" @click.stop="acknowledge(item)">
							{{ __("اتمام") }}
						</button>
					</div>
					<div class="oa-actions" v-else>
						<button class="btn btn-xs btn-primary" @click.stop="openReference(item)">
							{{ __("بازکردن") }}
						</button>
					</div>
				</div>
			</div>
		</section>

		<NewLetterForm
			v-if="showNewLetter"
			@close="showNewLetter = false"
			@created="onLetterCreated"
		/>
	</div>
</template>

<script>
const __ = window.__ || ((s) => s);
const API = "office_automation.office_automation.api.inbox.";
const REF = "office_automation.office_automation.doctype.document_referral.document_referral.";

import OaIcon from "./components/OaIcon.vue";
import NewLetterForm from "./NewLetterForm.vue";

const SCOPE_ICONS = {
	inbox: "inbox",
	outbox: "send",
	search: "search",
	yic: "folder",
	drafts: "file-text",
	visibility: "eye",
	settings: "settings",
};

export default {
	name: "InboxApp",
	components: { OaIcon, NewLetterForm },
	props: { page: { type: Object, default: null } },
	data() {
		return {
			activeFolder: "inbox:all",
			search: "",
			urgencyFilter: "",
			loading: false,
			showNewLetter: false,
			items: [],
			counts: { inbox: {}, outbox: {}, drafts: 0 },
			folders: [
				{ group: true, label: __("کارتابل دریافتی (Inbox)") },
				{ key: "inbox:all", label: __("همه"), scope: "inbox", folder: "all" },
				{ key: "inbox:order", label: __("دستور"), scope: "inbox", folder: "order", child: true },
				{ key: "inbox:followup", label: __("پیگیری"), scope: "inbox", folder: "followup", child: true },
				{ key: "inbox:action", label: __("اقدام"), scope: "inbox", folder: "action", child: true },
				{ key: "inbox:notification", label: __("استحضار"), scope: "inbox", folder: "notification", child: true },
				{ key: "inbox:info", label: __("اطلاع"), scope: "inbox", folder: "info", child: true },

				{ group: true, label: __("کارتابل ارسالی (Outbox)") },
				{ key: "outbox:all", label: __("همه"), scope: "outbox", state: "all" },
				{ key: "outbox:in_progress", label: __("در دست اقدام"), scope: "outbox", state: "in_progress", child: true },
				{ key: "outbox:approved", label: __("تأیید شده‌ها"), scope: "outbox", state: "approved", child: true },
				{ key: "outbox:rejected", label: __("رد شده‌ها"), scope: "outbox", state: "rejected", child: true },

				{ group: true, label: __("سایر") },
				{ key: "search", label: __("جستجو"), scope: "search" },
				{ key: "yic", label: __("کارتابل YIC"), scope: "yic" },
				{ key: "drafts", label: __("پیش‌نویس‌ها"), scope: "drafts" },
				{ key: "private", label: __("خصوصی"), scope: "visibility", visibility: "private", child: true },
				{ key: "public", label: __("عمومی"), scope: "visibility", visibility: "public", child: true },
				{ key: "settings", label: __("تنظیمات"), scope: "settings" },
			],
		};
	},
	computed: {
		activeNode() {
			return this.folders.find((f) => !f.group && f.key === this.activeFolder) || {};
		},
		activeLabel() {
			return this.activeNode.label || __("کارتابل");
		},
		scope() {
			return this.activeNode.scope;
		},
		filteredItems() {
			const q = this.search.trim().toLowerCase();
			return this.items.filter((item) => {
				if (this.urgencyFilter && item.urgency !== this.urgencyFilter) return false;
				if (!q) return true;
				const hay = [
					item.title,
					item.subtitle,
					item.instruction,
					item.sender,
					item.recipient,
					item.referral_type,
					item.statusLabel,
				]
					.filter(Boolean)
					.join(" ")
					.toLowerCase();
				return q.split(/\s+/).every((t) => hay.includes(t));
			});
		},
	},
	mounted() {
		this.refresh();
		this._onUpdate = () => this.refresh();
		frappe.realtime.on("oa_inbox_update", this._onUpdate);
	},
	beforeUnmount() {
		if (this._onUpdate) frappe.realtime.off("oa_inbox_update", this._onUpdate);
	},
	methods: {
		__,
		badge(node) {
			if (node.scope === "inbox") return this.counts.inbox?.[node.folder] || null;
			if (node.scope === "outbox") return this.counts.outbox?.[node.state] || null;
			if (node.scope === "drafts") return this.counts.drafts || null;
			return null;
		},
		async refresh() {
			await Promise.all([this.loadFolder(), this.loadCounts()]);
		},
		async loadCounts() {
			try {
				this.counts = await frappe.xcall(API + "get_folder_counts");
			} catch (e) {
				/* decorative */
			}
		},
		selectFolder(node) {
			this.activeFolder = node.key;
			if (node.scope === "settings") {
				frappe.set_route("Form", "Office Automation Settings");
				return;
			}
			if (node.scope === "search") {
				this.$nextTick(() => this.$refs.search && this.$refs.search.focus());
			}
			this.loadFolder();
		},
		async loadFolder() {
			const node = this.activeNode;
			if (!node.scope || node.scope === "settings") return;
			this.loading = true;
			try {
				let raw = [];
				if (node.scope === "inbox" || node.scope === "search") {
					raw = await frappe.xcall(API + "get_inbox_items", {
						folder: node.folder || "all",
					});
					this.items = raw.map(this.normalizeReferral);
				} else if (node.scope === "outbox") {
					raw = await frappe.xcall(API + "get_outbox_items", { state: node.state });
					this.items = raw.map(this.normalizeReferral);
				} else if (node.scope === "yic") {
					raw = await frappe.xcall(API + "get_yic_items");
					this.items = raw.map(this.normalizeReferral);
				} else if (node.scope === "drafts") {
					raw = await frappe.xcall(API + "get_drafts");
					this.items = raw.map(this.normalizeLetter);
				} else if (node.scope === "visibility") {
					raw = await frappe.xcall(API + "get_letters_by_visibility", {
						visibility: node.visibility,
					});
					this.items = raw.map(this.normalizeLetter);
				}
			} catch (e) {
				frappe.msgprint(__("بارگذاری انجام نشد."));
				this.items = [];
			} finally {
				this.loading = false;
			}
		},
		normalizeReferral(r) {
			return {
				...r,
				kind: "referral",
				title: r.reference_title,
				subtitle: `${r.reference_doctype} · ${r.reference_name}`,
				statusLabel: this.faStatus(r),
			};
		},
		normalizeLetter(l) {
			return {
				...l,
				kind: "letter",
				reference_doctype: "Automation Letter",
				reference_name: l.name,
				title: l.subject || l.name,
				subtitle: [l.letter_no, l.letter_type].filter(Boolean).join(" · "),
				statusLabel: l.status,
			};
		},
		needsDecision(item) {
			return !item.is_cc && ["Order", "Follow-up", "Action"].includes(item.referral_type);
		},
		async openItem(item) {
			if (item.kind === "referral" && this.scope === "inbox" && item.status === "Unseen") {
				try {
					await frappe.xcall(REF + "mark_referral_seen", { referral: item.name });
					item.status = "Seen";
					item.statusLabel = this.faStatus(item);
					this.loadCounts();
				} catch (e) {
					/* ignore */
				}
			}
		},
		openReference(item) {
			frappe.set_route("Form", item.reference_doctype, item.reference_name);
		},
		async acknowledge(item) {
			await frappe.xcall(REF + "mark_referral_actioned", { referral: item.name });
			frappe.show_alert({ message: __("انجام شد"), indicator: "green" });
			this.refresh();
		},
		decide(item, kind) {
			const isApprove = kind === "approve";
			const d = new frappe.ui.Dialog({
				title: isApprove ? __("تأیید ارجاع") : __("رد / بازگشت ارجاع"),
				fields: [
					{ label: __("یادداشت (توضیحات ارجاع)"), fieldname: "note", fieldtype: "Small Text" },
				],
				primary_action_label: isApprove ? __("تأیید") : __("رد"),
				primary_action: async (v) => {
					await frappe.xcall(REF + (isApprove ? "approve_referral" : "reject_referral"), {
						referral: item.name,
						note: v.note,
					});
					d.hide();
					frappe.show_alert({
						message: isApprove ? __("تأیید شد") : __("رد شد"),
						indicator: isApprove ? "green" : "red",
					});
					this.refresh();
				},
			});
			d.show();
		},
		forward(item) {
			const d = new frappe.ui.Dialog({
				title: __("ارجاع (Erja)"),
				fields: [
					{ label: __("گیرنده"), fieldname: "recipient", fieldtype: "Link", options: "User", reqd: 1 },
					{
						label: __("نوع ارجاع"),
						fieldname: "referral_type",
						fieldtype: "Select",
						options: "Order\nFollow-up\nAction\nNotification\nInfo",
						default: "Action",
					},
					{ label: __("نوع اقدام"), fieldname: "action_type", fieldtype: "Link", options: "Action Type" },
					{ label: __("توضیحات ارجاع"), fieldname: "instruction", fieldtype: "Small Text" },
				],
				primary_action_label: __("ارجاع"),
				primary_action: async (v) => {
					await frappe.xcall(REF + "forward_document", {
						doc_type: item.reference_doctype,
						doc_name: item.reference_name,
						recipient: v.recipient,
						referral_type: v.referral_type,
						action_type: v.action_type,
						instruction: v.instruction,
						parent_referral: item.kind === "referral" ? item.name : null,
					});
					d.hide();
					frappe.show_alert({ message: __("ارجاع شد به {0}", [v.recipient]), indicator: "green" });
					this.refresh();
				},
			});
			d.show();
		},
		createLetter() {
			this.showNewLetter = true;
		},
		onLetterCreated({ name, refer }) {
			this.showNewLetter = false;
			this.refresh();
			if (refer && name) {
				this.forward({
					kind: "letter",
					reference_doctype: "Automation Letter",
					reference_name: name,
				});
			}
		},
		folderIcon(node) {
			return SCOPE_ICONS[node.scope] || "chevron-right";
		},
		cardClass(item) {
			return {
				unseen: item.kind === "referral" && item.status === "Unseen",
				immediate: item.urgency === "Immediate",
				urgent: item.urgency === "Urgent",
			};
		},
		statusColor(item) {
			if (item.outcome === "Approved") return "green";
			if (item.outcome === "Rejected") return "red";
			return { Draft: "gray", Unseen: "orange", Seen: "blue", Actioned: "green" }[item.status] || "gray";
		},
		faStatus(r) {
			if (r.outcome === "Approved") return __("تأیید شده");
			if (r.outcome === "Rejected") return __("رد شده");
			return { Unseen: __("دیده‌نشده"), Seen: __("دیده‌شده"), Actioned: __("اتمام‌یافته"), Draft: __("پیش‌نویس") }[r.status] || r.status;
		},
		faType(t) {
			return { Order: __("دستور"), "Follow-up": __("پیگیری"), Action: __("اقدام"), Notification: __("استحضار"), Info: __("اطلاع") }[t] || t;
		},
		faUrgency(u) {
			return { Urgent: __("فوری"), Immediate: __("آنی"), Normal: __("عادی") }[u] || u;
		},
		faConf(c) {
			return { Confidential: __("محرمانه"), Secret: __("سری"), Normal: __("عادی") }[c] || c;
		},
		prettyTime(dt) {
			return frappe.datetime.comment_when ? frappe.datetime.comment_when(dt) : dt;
		},
	},
};
</script>

<style scoped>
.oa-cartable {
	display: flex;
	gap: 16px;
	align-items: flex-start;
}
.oa-sidebar {
	flex: 0 0 248px;
	border: 1px solid var(--oa-border, #eceef1);
	border-radius: 14px;
	padding: 12px;
	background: var(--oa-surface, #fff);
	box-shadow: var(--oa-shadow-sm);
	position: sticky;
	top: 12px;
}
.oa-new-btn {
	width: 100%;
	margin-bottom: 12px;
}
.oa-group-title {
	font-size: 11px;
	font-weight: 700;
	color: var(--text-muted, #8d99a6);
	margin: 12px 6px 4px;
	text-transform: uppercase;
}
.oa-folder {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 6px 10px;
	border-radius: 6px;
	color: var(--text-color, #1f272e);
	text-decoration: none;
	font-size: 13px;
}
.oa-folder.child {
	padding-inline-start: 22px;
	font-size: 12.5px;
}
.oa-folder:hover {
	background: var(--bg-light-gray, #f4f5f6);
}
.oa-folder.active {
	background: var(--bg-blue, #e7f0ff);
	color: var(--blue-600, #1565d8);
	font-weight: 600;
}
.oa-count {
	background: var(--gray-400, #b8c2cc);
	color: #fff;
	border-radius: 10px;
	padding: 0 7px;
	font-size: 11px;
}
.oa-main {
	flex: 1 1 auto;
	min-width: 0;
}
.oa-main-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 12px;
	margin-bottom: 12px;
	flex-wrap: wrap;
}
.oa-title {
	margin: 0;
}
.oa-tools {
	display: flex;
	gap: 8px;
	align-items: center;
	flex-wrap: wrap;
}
.oa-search {
	max-width: 320px;
}
.oa-mini {
	max-width: 150px;
}
.oa-card {
	border: 1px solid var(--oa-border, #eceef1);
	border-radius: 12px;
	padding: 14px 16px;
	margin-bottom: 12px;
	cursor: pointer;
	background: var(--oa-surface, #fff);
	box-shadow: var(--oa-shadow-sm);
	transition: box-shadow 0.15s ease, transform 0.05s ease;
}
.oa-card:hover {
	box-shadow: var(--oa-shadow-md);
}
.oa-folder-label {
	display: flex;
	align-items: center;
	gap: 8px;
}
.oa-card.unseen {
	border-inline-start: 3px solid var(--orange-500, #f59e0b);
}
.oa-card.immediate {
	border-inline-start: 3px solid var(--red-500, #e03636);
}
.oa-card.urgent {
	border-inline-start: 3px solid var(--orange-400, #ff8c00);
}
.oa-card-head {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 8px;
	margin-bottom: 4px;
}
.oa-subject {
	font-weight: 600;
}
.oa-badges {
	display: flex;
	gap: 4px;
	flex-wrap: wrap;
}
.pill {
	display: inline-block;
	font-size: 10px;
	padding: 1px 8px;
	border-radius: 10px;
	background: #eef1f4;
	color: #5e6d7a;
}
.pill.urgent {
	background: #fff3e0;
	color: #c25700;
}
.pill.conf {
	background: #fde8e8;
	color: #b42318;
}
.pill.cc {
	background: #eef2ff;
	color: #3538cd;
}
.pill.green {
	background: #e6f4ea;
	color: #137333;
}
.pill.red {
	background: #fde8e8;
	color: #b42318;
}
.pill.orange {
	background: #fff3e0;
	color: #c25700;
}
.pill.blue {
	background: #e7f0ff;
	color: #1565d8;
}
.pill.gray {
	background: #eef1f4;
	color: #5e6d7a;
}
.oa-meta {
	display: flex;
	justify-content: space-between;
	gap: 8px;
	font-size: 12px;
	margin-bottom: 6px;
	flex-wrap: wrap;
}
.oa-instruction {
	font-size: 13px;
	white-space: pre-wrap;
	margin-bottom: 8px;
}
.oa-actions {
	display: flex;
	gap: 6px;
	flex-wrap: wrap;
}
.oa-empty {
	padding: 40px;
	text-align: center;
}
</style>
