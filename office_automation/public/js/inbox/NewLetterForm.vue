<template>
	<Transition name="oa-fade">
		<div class="oa-ui oa-modal-backdrop" @click.self="close">
			<Transition name="oa-pop" appear>
				<div class="oa-modal" role="dialog" aria-modal="true">
					<header class="oa-modal-head">
						<h3 style="display: flex; align-items: center; gap: 10px">
							<OaIcon name="file-text" :size="20" />
							{{ isEdit ? __("ویرایش پیش‌نویس") : __("ایجاد نامه جدید") }}
						</h3>
						<button class="oa-btn oa-btn-subtle" @click="close" :aria-label="__('بستن')">
							<OaIcon name="x" :size="18" />
						</button>
					</header>

					<div class="oa-modal-body">
						<!-- Date + classification -->
						<section class="oa-section">
							<div class="oa-grid-2">
								<div>
									<label class="oa-label">{{ __("تاریخ") }}</label>
									<OaSegmented v-model="dateChoice" :options="dateOptions" @update:modelValue="syncDate" />
								</div>
								<div>
									<label class="oa-label">{{ __("نوع نامه") }}</label>
									<OaSegmented v-model="letterType" :options="letterTypeOptions" />
								</div>
							</div>

							<div class="oa-grid-2" style="margin-top: 20px">
								<div>
									<label class="oa-label">{{ __("محرمانگی") }}</label>
									<OaSegmented v-model="confidentiality" :options="confOptions" />
								</div>
								<div>
									<label class="oa-label">{{ __("فوریت") }}</label>
									<OaSegmented v-model="urgency" :options="urgencyOptions" />
								</div>
							</div>

							<label class="oa-toggle" style="margin-top: 20px">
								<input type="checkbox" v-model="isPrivate" />
								<span class="oa-track"><span class="oa-thumb" /></span>
								<span style="display: flex; align-items: center; gap: 6px">
									<OaIcon name="lock" :size="15" /> {{ __("خصوصی (فقط طرف‌های نامه)") }}
								</span>
							</label>
						</section>

						<!-- Recipients & CC -->
						<section class="oa-section">
							<div class="oa-section-title"><OaIcon name="users" :size="17" /> {{ __("گیرندگان") }}</div>
							<label class="oa-label">{{ __("گیرندگان اصلی") }}</label>
							<OaUserChips v-model="recipients" :placeholder="__('نام کارمند را تایپ کنید…')" />

							<div style="margin-top: 16px">
								<label class="oa-label">{{ __("نوع ارجاع برای گیرندگان") }}</label>
								<OaSegmented v-model="referralType" :options="typeOptions" />
							</div>

							<div style="margin-top: 16px">
								<label class="oa-label">{{ __("رونوشت (CC)") }}</label>
								<OaUserChips v-model="cc" :placeholder="__('گیرندگان رونوشت…')" />
								<div class="oa-help">{{ __("گیرندگان رونوشت نامه را در پوشهٔ اطلاع دریافت می‌کنند.") }}</div>
							</div>
						</section>

						<!-- Subject & body -->
						<section class="oa-section">
							<div class="oa-section-title"><OaIcon name="mail" :size="17" /> {{ __("متن نامه") }}</div>
							<label class="oa-label">{{ __("موضوع") }} *</label>
							<input
								v-model="subject"
								class="oa-input"
								:placeholder="__('موضوع نامه')"
								@input="error = ''"
							/>
							<label class="oa-label" style="margin-top: 16px">{{ __("متن") }}</label>
							<OaEditor v-model="body" />
						</section>

						<!-- Attachments -->
						<section class="oa-section">
							<div class="oa-section-title"><OaIcon name="paperclip" :size="17" /> {{ __("پیوست‌ها") }}</div>
							<OaDropzone v-model="attachments" />
						</section>

						<Transition name="oa-slide">
							<div v-if="error" class="oa-error">
								<OaIcon name="alert-triangle" :size="15" /> {{ error }}
							</div>
						</Transition>
					</div>

					<footer class="oa-modal-foot">
						<button class="oa-btn oa-btn-ghost" :disabled="busy" @click="close">
							{{ __("انصراف") }}
						</button>
						<button class="oa-btn oa-btn-ghost" :disabled="busy" @click="save(false)">
							{{ __("ثبت پیش‌نویس") }}
						</button>
						<button class="oa-btn oa-btn-ghost" :disabled="busy" @click="save(true, true)">
							<OaIcon name="forward" :size="16" /> {{ __("ثبت و ارجاع") }}
						</button>
						<button class="oa-btn oa-btn-primary" :disabled="busy" @click="save(true)">
							<OaIcon name="send" :size="16" /> {{ __("ثبت") }}
						</button>
					</footer>
				</div>
			</Transition>
		</div>
	</Transition>
</template>

<script>
const __ = window.__ || ((s) => s);
import OaIcon from "./components/OaIcon.vue";
import OaSegmented from "./components/OaSegmented.vue";
import OaUserChips from "./components/OaUserChips.vue";
import OaDropzone from "./components/OaDropzone.vue";
import OaEditor from "./OaEditor.vue";

const LETTER_API = "office_automation.office_automation.api.letter.";

export default {
	name: "NewLetterForm",
	components: { OaIcon, OaSegmented, OaUserChips, OaDropzone, OaEditor },
	props: {
		referLetter: { type: Object, default: null },
		// Name of an existing draft to edit. When set, the form loads and updates
		// that letter instead of creating a new one.
		editLetter: { type: String, default: null },
	},
	emits: ["close", "created"],
	data() {
		return {
			dateChoice: "today",
			date: frappe.datetime.get_today(),
			// Pre-selected from Office Automation Settings (default_letter_type) in
			// mounted(), so it matches whatever each site names its types.
			letterType: "",
			letterTypes: [],
			confidentiality: "Normal",
			urgency: "Normal",
			isPrivate: false,
			recipients: [],
			cc: [],
			referralType: "Action",
			subject: "",
			body: "",
			attachments: [],
			busy: false,
			error: "",
			dateOptions: [
				{ value: "today", label: __("امروز") },
				{ value: "yesterday", label: __("دیروز") },
			],
			confOptions: [
				{ value: "Normal", label: __("عادی") },
				{ value: "Confidential", label: __("محرمانه"), tone: "warn", icon: "lock" },
				{ value: "Secret", label: __("سری"), tone: "danger", icon: "lock" },
			],
			urgencyOptions: [
				{ value: "Normal", label: __("عادی") },
				{ value: "Urgent", label: __("فوری"), tone: "warn" },
				{ value: "Immediate", label: __("آنی"), tone: "danger" },
			],
			typeOptions: [
				{ value: "Order", label: __("دستور") },
				{ value: "Follow-up", label: __("پیگیری") },
				{ value: "Action", label: __("اقدام") },
				{ value: "Notification", label: __("استحضار") },
				{ value: "Info", label: __("اطلاع") },
			],
		};
	},
	computed: {
		// Letter Type as a segmented control (same UX as محرمانگی).
		letterTypeOptions() {
			return this.letterTypes.map((t) => ({ value: t, label: t }));
		},
		isEdit() {
			return !!this.editLetter;
		},
	},
	async mounted() {
		// Body uses the TipTap-based OaEditor (v-model="body").
		try {
			this.letterTypes = await frappe.db.get_list("Letter Type", {
				filters: { is_active: 1 },
				pluck: "name",
				limit: 50,
			});
		} catch (e) {
			/* optional */
		}
		// Pre-select the org's configured default type for NEW letters only.
		if (!this.isEdit) {
			try {
				const dft = await frappe.xcall(LETTER_API + "get_default_letter_type");
				if (dft && this.letterTypes.includes(dft)) this.letterType = dft;
			} catch (e) {
				/* optional */
			}
		}
		if (this.isEdit) await this.loadForEdit();
	},
	methods: {
		__,
		async loadForEdit() {
			try {
				const d = await frappe.xcall(LETTER_API + "get_letter_for_edit", { name: this.editLetter });
				this.subject = d.subject || "";
				this.date = d.date || frappe.datetime.get_today();
				const today = frappe.datetime.get_today();
				const yesterday = frappe.datetime.add_days(today, -1);
				this.dateChoice = this.date === yesterday ? "yesterday" : "today";
				this.letterType = d.letter_type || "";
				this.confidentiality = d.confidentiality || "Normal";
				this.urgency = d.urgency || "Normal";
				this.isPrivate = !!d.is_private;
				this.recipients = (d.recipients || []).map((r) => ({ value: r.recipient, label: r.recipient_name || r.recipient }));
				this.referralType = (d.recipients && d.recipients[0] && d.recipients[0].referral_type) || "Action";
				this.cc = (d.cc || []).map((c) => ({ value: c.recipient, label: c.recipient_name || c.recipient }));
				this.attachments = (d.attachments || []).map((a) => ({ title: a.title, file_url: a.file_url }));
				this.body = d.body || "";
				// Remember per-recipient fields the composer UI can't show, so a save
				// preserves them instead of clearing action_type/instruction and
				// flattening differing referral types.
				this._recipientMeta = {};
				(d.recipients || []).forEach((r) => {
					this._recipientMeta[r.recipient] = {
						referral_type: r.referral_type,
						action_type: r.action_type,
						instruction: r.instruction,
					};
				});
				this._initialReferralType = this.referralType;
			} catch (e) {
				// Don't leave a blank but editable form open — saving it would wipe
				// the draft's recipients/attachments. Surface the error and close.
				frappe.msgprint((e && e.message) || __("بارگذاری پیش‌نویس ناموفق بود."));
				this.$emit("close");
			}
		},
		syncDate(choice) {
			this.date =
				choice === "yesterday"
					? frappe.datetime.add_days(frappe.datetime.get_today(), -1)
					: frappe.datetime.get_today();
		},
		close() {
			if (!this.busy) this.$emit("close");
		},
		async save(submit, refer = false) {
			this.error = "";
			if (!this.subject.trim()) {
				this.error = __("موضوع نامه الزامی است.");
				return;
			}
			if (submit && !this.recipients.length) {
				this.error = __("برای ثبت و ارسال، حداقل یک گیرنده لازم است.");
				return;
			}
			this.busy = true;
			try {
				const payload = {
					subject: this.subject,
					body: this.body,
					date: this.date,
					letter_type: this.letterType || null,
					confidentiality: this.confidentiality,
					urgency: this.urgency,
					is_private: this.isPrivate ? 1 : 0,
					recipients: this.recipients.map((r) => {
						const meta = this._recipientMeta && this._recipientMeta[r.value];
						// Keep each recipient's original referral type unless the user
						// changed the (single) selector; new recipients use the current one.
						const typeChanged = this.isEdit && this.referralType !== this._initialReferralType;
						return {
							recipient: r.value,
							referral_type: meta && !typeChanged ? meta.referral_type || this.referralType : this.referralType,
							action_type: meta ? meta.action_type : undefined,
							instruction: meta ? meta.instruction : undefined,
						};
					}),
					cc: this.cc.map((c) => ({ recipient: c.value })),
					attachments: this.attachments,
				};
				const args = { payload: JSON.stringify(payload), submit: submit ? 1 : 0 };
				if (this.isEdit) args.name = this.editLetter;
				const res = await frappe.xcall(LETTER_API + (this.isEdit ? "update_letter" : "create_letter"), args);
				frappe.show_alert({
					message: submit
						? __("نامه ثبت و ارسال شد")
						: this.isEdit
							? __("پیش‌نویس به‌روزرسانی شد")
							: __("پیش‌نویس ذخیره شد"),
					indicator: "green",
				});
				this.$emit("created", { name: res.name, refer });
			} catch (e) {
				this.error = (e && e.message) || __("ثبت ناموفق بود.");
			} finally {
				this.busy = false;
			}
		},
	},
};
</script>

<style scoped>
.oa-error {
	display: flex;
	align-items: center;
	gap: 8px;
	color: var(--oa-danger);
	background: color-mix(in srgb, var(--oa-danger) 12%, var(--oa-surface));
	border: 1px solid color-mix(in srgb, var(--oa-danger) 35%, var(--oa-surface));
	border-radius: 8px;
	padding: 10px 12px;
	font-size: 13px;
}
.oa-toggle {
	display: inline-flex;
	align-items: center;
	gap: 10px;
	cursor: pointer;
	font-size: 13px;
	user-select: none;
}
.oa-toggle input {
	display: none;
}
.oa-track {
	width: 38px;
	height: 22px;
	border-radius: 999px;
	background: var(--oa-border);
	position: relative;
	transition: background 0.18s ease;
}
.oa-thumb {
	position: absolute;
	top: 2px;
	left: 2px;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	background: #fff;
	box-shadow: var(--oa-shadow-sm);
	transition: transform 0.18s ease;
}
.oa-toggle input:checked + .oa-track {
	background: var(--oa-primary);
}
.oa-toggle input:checked + .oa-track .oa-thumb {
	transform: translateX(16px);
}
</style>
