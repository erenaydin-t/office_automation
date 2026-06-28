<template>
	<div>
		<div
			class="oa-dropzone"
			:class="{ dragging }"
			@click="$refs.file.click()"
			@dragover.prevent="dragging = true"
			@dragleave.prevent="dragging = false"
			@drop.prevent="onDrop"
		>
			<div style="display: flex; flex-direction: column; align-items: center; gap: 8px">
				<OaIcon name="upload-cloud" :size="30" />
				<div style="font-weight: 500">{{ __("فایل‌ها را اینجا رها کنید یا کلیک کنید") }}</div>
				<div class="oa-help">{{ __("آپلود از سیستم، اسناد موجود یا اسکنر") }}</div>
			</div>
			<input ref="file" type="file" multiple hidden @change="onPick" />
		</div>

		<TransitionGroup name="oa-slide">
			<div v-for="(f, i) in files" :key="f.uid" class="oa-file-row">
				<span style="display: flex; align-items: center; gap: 8px; min-width: 0">
					<OaIcon name="paperclip" :size="15" />
					<span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
						{{ f.name }}
					</span>
					<small v-if="f.uploading" class="oa-help">{{ __("در حال آپلود…") }}</small>
					<OaIcon v-else-if="f.file_url" name="check-circle" :size="14" />
				</span>
				<span class="oa-chip-x" @click="remove(i)"><OaIcon name="x" :size="14" /></span>
			</div>
		</TransitionGroup>
	</div>
</template>

<script>
const __ = window.__ || ((s) => s);
import OaIcon from "./OaIcon.vue";

let uid = 0;

export default {
	name: "OaDropzone",
	components: { OaIcon },
	props: {
		// modelValue: [{ title, file_url }]
		modelValue: { type: Array, default: () => [] },
	},
	emits: ["update:modelValue"],
	data() {
		return { dragging: false, files: [] };
	},
	watch: {
		// Seed the internal list once when the parent supplies initial files
		// (edit mode). Guarded so it never clobbers files the user is editing.
		modelValue: {
			immediate: true,
			handler(val) {
				if (val && val.length && !this.files.length) {
					this.files = val.map((f) => ({
						uid: ++uid,
						name: f.title || f.file_url,
						uploading: false,
						file_url: f.file_url,
					}));
				}
			},
		},
	},
	methods: {
		__,
		onDrop(e) {
			this.dragging = false;
			this.addFiles(e.dataTransfer.files);
		},
		onPick(e) {
			this.addFiles(e.target.files);
			e.target.value = "";
		},
		addFiles(fileList) {
			[...fileList].forEach((file) => {
				const entry = { uid: ++uid, name: file.name, uploading: true, file_url: null };
				this.files.push(entry);
				// Track by uid and mutate through the reactive array (not this raw
				// `entry` ref) so status changes actually re-render the row.
				this.upload(file, entry.uid);
			});
		},
		async upload(file, fileUid) {
			try {
				const form = new FormData();
				form.append("file", file, file.name);
				form.append("is_private", 1);
				form.append("folder", "Home");
				const res = await fetch("/api/method/upload_file", {
					method: "POST",
					headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
					body: form,
				});
				const data = await res.json().catch(() => ({}));
				const fileUrl = data && data.message && data.message.file_url;
				if (!res.ok || !fileUrl) {
					throw new Error(this.serverError(data) || __("آپلود ناموفق بود."));
				}
				this.patch(fileUid, { file_url: fileUrl, uploading: false });
				this.sync();
			} catch (e) {
				this.patch(fileUid, { uploading: false });
				frappe.show_alert({
					message: (e && e.message) || __("آپلود ناموفق: {0}", [file.name]),
					indicator: "red",
				});
			}
		},
		patch(fileUid, changes) {
			// Look the entry up in the reactive array so the assignment is tracked.
			const f = this.files.find((x) => x.uid === fileUid);
			if (f) Object.assign(f, changes);
		},
		serverError(data) {
			// Frappe encodes user-facing errors in _server_messages (JSON of JSON).
			try {
				const msgs = JSON.parse((data && data._server_messages) || "[]");
				if (msgs.length) return JSON.parse(msgs[0]).message;
			} catch (e) {
				/* fall through */
			}
			return (data && data.exception) || "";
		},
		remove(i) {
			this.files.splice(i, 1);
			this.sync();
		},
		sync() {
			this.$emit(
				"update:modelValue",
				this.files
					.filter((f) => f.file_url)
					.map((f) => ({ title: f.name, file_url: f.file_url }))
			);
		},
	},
};
</script>
