<template>
	<Transition name="oa-fade">
		<div class="oa-ui oa-modal-backdrop" @click.self="close">
			<Transition name="oa-pop" appear>
				<div class="oa-modal" role="dialog" aria-modal="true" style="max-width: 520px">
					<header class="oa-modal-head">
						<h3 style="display: flex; align-items: center; gap: 10px">
							<OaIcon name="forward" :size="20" />
							{{ __("ارجاع (Erja)") }}
						</h3>
						<button class="oa-btn oa-btn-subtle" @click="close" :aria-label="__('بستن')">
							<OaIcon name="x" :size="18" />
						</button>
					</header>

					<div class="oa-modal-body">
						<section class="oa-section">
							<label class="oa-label">{{ __("گیرنده") }} *</label>
							<OaUserChips v-model="recipients" :placeholder="__('نام کارمند را تایپ کنید…')" />
							<div class="oa-help">{{ __("می‌توانید به چند نفر همزمان ارجاع دهید.") }}</div>

							<div style="margin-top: 18px">
								<label class="oa-label">{{ __("نوع ارجاع") }}</label>
								<OaSegmented v-model="referralType" :options="typeOptions" />
							</div>

							<div style="margin-top: 18px">
								<label class="oa-label">{{ __("توضیحات ارجاع") }}</label>
								<textarea
									v-model="instruction"
									class="oa-textarea"
									:placeholder="__('توضیحات ارجاع…')"
									@input="error = ''"
								/>
							</div>

							<div style="margin-top: 18px">
								<label class="oa-label">{{ __("پیوست") }}</label>
								<OaDropzone v-model="attachments" />
							</div>

							<Transition name="oa-slide">
								<div v-if="error" class="oa-error">
									<OaIcon name="alert-triangle" :size="15" /> {{ error }}
								</div>
							</Transition>
						</section>
					</div>

					<footer class="oa-modal-foot">
						<button class="oa-btn oa-btn-ghost" :disabled="busy" @click="close">
							{{ __("انصراف") }}
						</button>
						<button class="oa-btn oa-btn-primary" :disabled="busy" @click="submit">
							<OaIcon name="forward" :size="16" /> {{ __("ارجاع") }}
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

const REF = "office_automation.office_automation.doctype.document_referral.document_referral.";

export default {
	name: "OaReferForm",
	components: { OaIcon, OaSegmented, OaUserChips, OaDropzone },
	props: {
		// The referenced document being referred (e.g. an Automation Letter).
		doctype: { type: String, required: true },
		docName: { type: String, required: true },
		// The inbox item being acted upon, so forwarding it closes that node.
		parent: { type: String, default: null },
	},
	emits: ["close", "done"],
	data() {
		return {
			recipients: [],
			referralType: "Action",
			instruction: "",
			attachments: [],
			busy: false,
			error: "",
			typeOptions: [
				{ value: "Order", label: __("دستور") },
				{ value: "Follow-up", label: __("پیگیری") },
				{ value: "Action", label: __("اقدام") },
				{ value: "Notification", label: __("استحضار") },
				{ value: "Info", label: __("اطلاع") },
			],
		};
	},
	methods: {
		__,
		close() {
			if (!this.busy) this.$emit("close");
		},
		async submit() {
			this.error = "";
			if (!this.recipients.length) {
				this.error = __("انتخاب حداقل یک گیرنده الزامی است.");
				return;
			}
			this.busy = true;
			try {
				// Document Referral carries a single attachment; use the first file.
				const attachment = (this.attachments[0] && this.attachments[0].file_url) || null;
				// Fan out one referral per selected recipient, under the same parent.
				for (const r of this.recipients) {
					await frappe.xcall(REF + "forward_document", {
						doc_type: this.doctype,
						doc_name: this.docName,
						recipient: r.value,
						referral_type: this.referralType,
						instruction: this.instruction,
						attachment,
						parent_referral: this.parent,
					});
				}
				frappe.show_alert({ message: __("ارجاع شد"), indicator: "green" });
				this.$emit("done");
			} catch (e) {
				this.error = (e && e.message) || __("ارجاع ناموفق بود.");
			} finally {
				this.busy = false;
			}
		},
	},
};
</script>
