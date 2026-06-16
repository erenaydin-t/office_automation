<template>
	<div class="oa-inbox">
		<!-- Toolbar: tabs + search + filters -->
		<div class="oa-toolbar">
			<ul class="nav nav-tabs oa-tabs">
				<li v-for="tab in tabs" :key="tab.key" class="nav-item">
					<a
						class="nav-link"
						:class="{ active: activeTab === tab.key }"
						href="#"
						@click.prevent="setTab(tab.key)"
					>
						{{ tab.label }}
						<span v-if="counts[tab.countKey]" class="badge oa-badge">
							{{ counts[tab.countKey] }}
						</span>
					</a>
				</li>
			</ul>

			<div class="oa-filters">
				<input
					v-model="search"
					type="text"
					class="form-control oa-search"
					:placeholder="__('Semantic search: subject, instruction, sender…')"
				/>
				<select v-model="docTypeFilter" class="form-control oa-filter-select">
					<option value="">{{ __("All document types") }}</option>
					<option v-for="dt in availableDocTypes" :key="dt" :value="dt">
						{{ dt }}
					</option>
				</select>
				<button class="btn btn-default btn-sm" @click="refresh" :disabled="loading">
					<span v-if="loading">{{ __("Loading…") }}</span>
					<span v-else>{{ __("Refresh") }}</span>
				</button>
			</div>
		</div>

		<!-- List -->
		<div class="oa-list" v-if="!loading">
			<div v-if="!filteredItems.length" class="oa-empty text-muted">
				{{ __("No items.") }}
			</div>

			<div
				v-for="item in filteredItems"
				:key="item.name"
				class="oa-card"
				:class="{ unseen: item.status === 'Unseen' }"
				@click="openItem(item)"
			>
				<div class="oa-card-head">
					<span class="oa-subject">{{ item.reference_title }}</span>
					<span class="indicator-pill" :class="statusColor(item.status)">
						{{ __(item.status) }}
					</span>
				</div>
				<div class="oa-card-meta text-muted">
					<span>{{ item.reference_doctype }} · {{ item.reference_name }}</span>
					<span v-if="activeTab === 'sent'">→ {{ item.recipient }}</span>
					<span v-else>{{ __("from") }} {{ item.sender }}</span>
					<span v-if="item.action_type">· {{ item.action_type }}</span>
					<span class="oa-time">{{ prettyTime(item.creation) }}</span>
				</div>
				<div v-if="item.instruction" class="oa-instruction">
					{{ item.instruction }}
				</div>

				<div class="oa-card-actions" v-if="activeTab !== 'sent'">
					<button class="btn btn-xs btn-primary" @click.stop="openReference(item)">
						{{ __("Open") }}
					</button>
					<button class="btn btn-xs btn-default" @click.stop="forward(item)">
						{{ __("Forward (Erja)") }}
					</button>
					<button class="btn btn-xs btn-success" @click.stop="markActioned(item)">
						{{ __("Mark Actioned") }}
					</button>
				</div>
			</div>
		</div>

		<div v-else class="oa-loading text-muted">{{ __("Loading inbox…") }}</div>
	</div>
</template>

<script>
const __ = window.__ || ((s) => s);

export default {
	name: "InboxApp",
	props: {
		page: { type: Object, default: null },
	},
	data() {
		return {
			activeTab: "unread",
			search: "",
			docTypeFilter: "",
			loading: false,
			items: [],
			counts: { unread: 0, pending: 0, sent: 0 },
			tabs: [
				{ key: "unread", label: __("Unread"), countKey: "unread" },
				{ key: "pending", label: __("Pending Actions"), countKey: "pending" },
				{ key: "sent", label: __("Sent Referrals"), countKey: "sent" },
			],
		};
	},
	computed: {
		availableDocTypes() {
			return [...new Set(this.items.map((i) => i.reference_doctype))].sort();
		},
		filteredItems() {
			const q = this.search.trim().toLowerCase();
			return this.items.filter((item) => {
				if (this.docTypeFilter && item.reference_doctype !== this.docTypeFilter) {
					return false;
				}
				if (!q) return true;
				// Lightweight semantic-ish search across the meaningful fields.
				const haystack = [
					item.reference_title,
					item.reference_name,
					item.instruction,
					item.sender,
					item.recipient,
					item.action_type,
					item.status,
				]
					.filter(Boolean)
					.join(" ")
					.toLowerCase();
				// every search token must be present somewhere
				return q.split(/\s+/).every((token) => haystack.includes(token));
			});
		},
	},
	mounted() {
		this.refresh();
		// Live cartable: refresh when a new referral lands for this user.
		this._onInboxUpdate = (data) => {
			frappe.show_alert({
				message: __("New referral: {0}", [data.subject || ""]),
				indicator: "blue",
			});
			this.refresh();
		};
		frappe.realtime.on("oa_inbox_update", this._onInboxUpdate);
	},
	beforeUnmount() {
		if (this._onInboxUpdate) {
			frappe.realtime.off("oa_inbox_update", this._onInboxUpdate);
		}
	},
	methods: {
		__,
		setTab(key) {
			this.activeTab = key;
			this.loadItems();
		},
		async refresh() {
			await Promise.all([this.loadItems(), this.loadCounts()]);
		},
		async loadCounts() {
			try {
				this.counts = await frappe.xcall(
					"office_automation.office_automation.api.inbox.get_inbox_counts"
				);
			} catch (e) {
				// non-fatal: counts are decorative
			}
		},
		async loadItems() {
			this.loading = true;
			try {
				if (this.activeTab === "sent") {
					this.items = await frappe.xcall(
						"office_automation.office_automation.api.inbox.get_sent_referrals"
					);
				} else {
					const all = await frappe.xcall(
						"office_automation.office_automation.api.inbox.get_inbox_items"
					);
					this.items =
						this.activeTab === "unread"
							? all.filter((i) => i.status === "Unseen")
							: all.filter((i) => i.status === "Seen");
				}
			} catch (e) {
				frappe.msgprint(__("Could not load inbox items."));
				this.items = [];
			} finally {
				this.loading = false;
			}
		},
		async openItem(item) {
			if (item.status === "Unseen" && this.activeTab !== "sent") {
				try {
					await frappe.xcall(
						"office_automation.office_automation.doctype.document_referral.document_referral.mark_referral_seen",
						{ referral: item.name }
					);
					item.status = "Seen";
					this.loadCounts();
				} catch (e) {
					/* ignore */
				}
			}
		},
		openReference(item) {
			frappe.set_route("Form", item.reference_doctype, item.reference_name);
		},
		async markActioned(item) {
			await frappe.xcall(
				"office_automation.office_automation.doctype.document_referral.document_referral.mark_referral_actioned",
				{ referral: item.name }
			);
			frappe.show_alert({ message: __("Marked as actioned"), indicator: "green" });
			this.refresh();
		},
		forward(item) {
			const d = new frappe.ui.Dialog({
				title: __("Forward (Erja)"),
				fields: [
					{
						label: __("Recipient"),
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
				primary_action_label: __("Forward"),
				primary_action: async (values) => {
					await frappe.xcall(
						"office_automation.office_automation.doctype.document_referral.document_referral.forward_document",
						{
							doc_type: item.reference_doctype,
							doc_name: item.reference_name,
							recipient: values.recipient,
							instruction: values.instruction,
							action_type: values.action_type,
							parent_referral: item.name,
						}
					);
					d.hide();
					frappe.show_alert({
						message: __("Forwarded to {0}", [values.recipient]),
						indicator: "green",
					});
					this.refresh();
				},
			});
			d.show();
		},
		statusColor(status) {
			return (
				{ Draft: "gray", Unseen: "orange", Seen: "blue", Actioned: "green" }[status] ||
				"gray"
			);
		},
		prettyTime(dt) {
			return frappe.datetime.comment_when ? frappe.datetime.comment_when(dt) : dt;
		},
	},
};
</script>

<style scoped>
.oa-inbox {
	padding: 4px 0 24px;
}
.oa-toolbar {
	display: flex;
	flex-direction: column;
	gap: 12px;
	margin-bottom: 16px;
}
.oa-filters {
	display: flex;
	gap: 8px;
	align-items: center;
	flex-wrap: wrap;
}
.oa-search {
	max-width: 360px;
}
.oa-filter-select {
	max-width: 220px;
}
.oa-badge {
	background: var(--gray-600, #6b7280);
	color: #fff;
	margin-left: 6px;
}
.oa-card {
	border: 1px solid var(--border-color, #e2e2e2);
	border-radius: 8px;
	padding: 12px 14px;
	margin-bottom: 10px;
	cursor: pointer;
	transition: box-shadow 0.15s ease;
	background: var(--card-bg, #fff);
}
.oa-card:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.oa-card.unseen {
	border-left: 3px solid var(--orange-500, #f59e0b);
}
.oa-card-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 4px;
}
.oa-subject {
	font-weight: 600;
}
.oa-card-meta {
	display: flex;
	gap: 8px;
	flex-wrap: wrap;
	font-size: 12px;
	margin-bottom: 6px;
}
.oa-instruction {
	font-size: 13px;
	white-space: pre-wrap;
	margin-bottom: 8px;
}
.oa-card-actions {
	display: flex;
	gap: 6px;
}
.oa-empty,
.oa-loading {
	padding: 32px;
	text-align: center;
}
</style>
