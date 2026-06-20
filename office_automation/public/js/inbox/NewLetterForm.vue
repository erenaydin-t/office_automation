<template>
	<div class="oa-ui oa-compose-page">
		<div class="oa-compose-card">
			<header class="oa-modal-head">
				<h3 style="display: flex; align-items: center; gap: 10px">
					<OaIcon name="file-text" :size="20" />
					{{ __("ایجاد نامه جدید") }}
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
									<select v-model="letterType" class="oa-select">
										<option value="">{{ __("— انتخاب —") }}</option>
										<option v-for="t in letterTypes" :key="t" :value="t">{{ t }}</option>
									</select>
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
							<div ref="body" class="oa-body-editor"></div>
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
	</div>
</template>

<script>
const __ = window.__ || ((s) => s);
import OaIcon from "./components/OaIcon.vue";
import OaSegmented from "./components/OaSegmented.vue";
import OaUserChips from "./components/OaUserChips.vue";
import OaDropzone from "./components/OaDropzone.vue";

const LETTER_API = "office_automation.office_automation.api.letter.";

export default {
	name: "NewLetterForm",
	components: { OaIcon, OaSegmented, OaUserChips, OaDropzone },
	props: {
		referLetter: { type: Object, default: null },
	},
	emits: ["close", "created"],
	data() {
		return {
			dateChoice: "today",
			date: frappe.datetime.get_today(),
			letterType: "",
			letterTypes: [],
			confidentiality: "Normal",
			urgency: "Normal",
			isPrivate: false,
			recipients: [],
			cc: [],
			referralType: "Action",
			subject: "",
			attachments: [],
			busy: false,
			error: "",
			bodyControl: null,
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
	async mounted() {
		// Real WYSIWYG: reuse Frappe's Text Editor control.
		this.bodyControl = frappe.ui.form.make_control({
			df: { fieldtype: "Text Editor", fieldname: "body", label: "" },
			parent: this.$refs.body,
			render_input: true,
		});
		this.bodyControl.set_value("");
		try {
			this.letterTypes = await frappe.db.get_list("Letter Type", {
				filters: { is_active: 1 },
				pluck: "name",
				limit: 50,
			});
		} catch (e) {
			/* optional */
		}
	},
	methods: {
		__,
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
					body: this.bodyControl ? this.bodyControl.get_value() : "",
					date: this.date,
					letter_type: this.letterType || null,
					confidentiality: this.confidentiality,
					urgency: this.urgency,
					is_private: this.isPrivate ? 1 : 0,
					recipients: this.recipients.map((r) => ({
						recipient: r.value,
						referral_type: this.referralType,
					})),
					cc: this.cc.map((c) => ({ recipient: c.value })),
					attachments: this.attachments,
				};
				const res = await frappe.xcall(LETTER_API + "create_letter", {
					payload: JSON.stringify(payload),
					submit: submit ? 1 : 0,
				});
				frappe.show_alert({
					message: submit ? __("نامه ثبت و ارسال شد") : __("پیش‌نویس ذخیره شد"),
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
.oa-compose-card {
	background: var(--oa-surface);
	border: 1px solid var(--oa-border);
	border-radius: 16px;
	box-shadow: var(--oa-shadow-sm);
	overflow: hidden;
}
.oa-body-editor :deep(.ql-container) {
	border-radius: 0 0 8px 8px;
}
.oa-body-editor :deep(.ql-toolbar) {
	border-radius: 8px 8px 0 0;
}
.oa-error {
	display: flex;
	align-items: center;
	gap: 8px;
	color: var(--oa-danger);
	background: #fef2f2;
	border: 1px solid #fecaca;
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
	background: #d4d8de;
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
