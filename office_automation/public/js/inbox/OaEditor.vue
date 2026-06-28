<template>
	<div class="oa-editor" :data-tick="tick">
		<div v-if="editor" class="oa-editor-toolbar">
			<!-- Font family -->
			<select class="oa-tb-select" :value="currentFont" @change="setFont($event.target.value)" title="فونت">
				<option value="">فونت پیش‌فرض</option>
				<option v-for="f in fonts" :key="f.label" :value="f.stack" :style="{ fontFamily: f.stack }">{{ f.label }}</option>
			</select>
			<!-- Font size -->
			<select class="oa-tb-select" :value="currentSize" @change="setSize($event.target.value)" title="اندازه">
				<option value="">اندازه</option>
				<option v-for="s in sizes" :key="s" :value="s + 'px'">{{ faNum(s) }}</option>
			</select>
			<span class="oa-tb-sep"></span>
			<button type="button" class="oa-tb" :class="{ on: is('bold') }" @click="run('toggleBold')" title="درشت"><span class="ico">format_bold</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('italic') }" @click="run('toggleItalic')" title="کج"><span class="ico">format_italic</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('underline') }" @click="run('toggleUnderline')" title="زیرخط"><span class="ico">format_underlined</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('strike') }" @click="run('toggleStrike')" title="خط‌خورده"><span class="ico">format_strikethrough</span></button>
			<label class="oa-tb" title="رنگ متن" style="position:relative">
				<span class="ico">format_color_text</span>
				<input type="color" class="oa-color" @input="setColor($event.target.value)" />
			</label>
			<span class="oa-tb-sep"></span>
			<button type="button" class="oa-tb" :class="{ on: isHeading(2) }" @click="toggleHeading(2)" title="عنوان"><span class="ico">title</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('bulletList') }" @click="run('toggleBulletList')" title="فهرست نقطه‌ای"><span class="ico">format_list_bulleted</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('orderedList') }" @click="run('toggleOrderedList')" title="فهرست شماره‌دار"><span class="ico">format_list_numbered</span></button>
			<button type="button" class="oa-tb" :class="{ on: is('blockquote') }" @click="run('toggleBlockquote')" title="نقل‌قول"><span class="ico">format_quote</span></button>
			<span class="oa-tb-sep"></span>
			<button type="button" class="oa-tb" :class="{ on: isAlign('right') }" @click="setAlign('right')" title="راست‌چین"><span class="ico">format_align_right</span></button>
			<button type="button" class="oa-tb" :class="{ on: isAlign('center') }" @click="setAlign('center')" title="وسط‌چین"><span class="ico">format_align_center</span></button>
			<button type="button" class="oa-tb" :class="{ on: isAlign('left') }" @click="setAlign('left')" title="چپ‌چین"><span class="ico">format_align_left</span></button>
			<button type="button" class="oa-tb" :class="{ on: isAlign('justify') }" @click="setAlign('justify')" title="هم‌تراز"><span class="ico">format_align_justify</span></button>
			<span class="oa-tb-sep"></span>
			<button type="button" class="oa-tb" :class="{ on: is('link') }" @click="setLink" title="پیوند"><span class="ico">link</span></button>
			<button type="button" class="oa-tb" @click="run('unsetAllMarks')" title="پاک‌کردن قالب"><span class="ico">format_clear</span></button>
			<span class="oa-tb-sep"></span>
			<button type="button" class="oa-tb" @click="run('undo')" title="واگرد"><span class="ico">undo</span></button>
			<button type="button" class="oa-tb" @click="run('redo')" title="ازنو"><span class="ico">redo</span></button>
		</div>
		<EditorContent v-if="editor" :editor="editor" class="oa-editor-content" />
	</div>
</template>

<script>
import { markRaw } from "vue";
import { Editor, EditorContent } from "@tiptap/vue-3";
import { Extension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import TextStyle from "@tiptap/extension-text-style";
import FontFamily from "@tiptap/extension-font-family";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import { Color } from "@tiptap/extension-color";
import Link from "@tiptap/extension-link";

// Minimal font-size mark (extends TextStyle) — TipTap has no official one.
const FontSize = Extension.create({
	name: "fontSize",
	addOptions() {
		return { types: ["textStyle"] };
	},
	addGlobalAttributes() {
		return [
			{
				types: this.options.types,
				attributes: {
					fontSize: {
						default: null,
						parseHTML: (el) => el.style.fontSize || null,
						renderHTML: (attrs) => (attrs.fontSize ? { style: `font-size:${attrs.fontSize}` } : {}),
					},
				},
			},
		];
	},
	addCommands() {
		return {
			setFontSize:
				(size) =>
				({ chain }) =>
					chain().setMark("textStyle", { fontSize: size }).run(),
			unsetFontSize:
				() =>
				({ chain }) =>
					chain().setMark("textStyle", { fontSize: null }).removeEmptyTextStyle().run(),
		};
	},
});

// 10 Persian font families. Fonts are referenced by name (not bundled): each
// renders where the user has it installed; Tahoma is the shared fallback.
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export default {
	name: "OaEditor",
	components: { EditorContent },
	props: {
		modelValue: { type: String, default: "" },
	},
	emits: ["update:modelValue"],
	data() {
		return {
			editor: null,
			tick: 0,
			sizes: [12, 14, 16, 18, 20, 24, 28, 32],
			fonts: [
				{ label: "وزیرمتن", stack: "'Vazirmatn', Tahoma, sans-serif" },
				{ label: "شبنم", stack: "'Shabnam', Tahoma, sans-serif" },
				{ label: "ایران‌سنس", stack: "'IRANSans', 'IRANSansX', Tahoma, sans-serif" },
				{ label: "ب یکان", stack: "'B Yekan', 'BYekan', Tahoma, sans-serif" },
				{ label: "ب نازنین", stack: "'B Nazanin', 'BNazanin', Tahoma, serif" },
				{ label: "ب رویا", stack: "'B Roya', 'BRoya', Tahoma, serif" },
				{ label: "ب کودک", stack: "'B Koodak', 'BKoodak', Tahoma, sans-serif" },
				{ label: "ب تیتر", stack: "'B Titr', 'BTitr', Tahoma, sans-serif" },
				{ label: "ب میترا", stack: "'B Mitra', 'BMitra', Tahoma, serif" },
				{ label: "تاهوما", stack: "Tahoma, sans-serif" },
			],
		};
	},
	computed: {
		currentFont() {
			return (this.tick, this.editor ? this.editor.getAttributes("textStyle").fontFamily || "" : "");
		},
		currentSize() {
			return (this.tick, this.editor ? this.editor.getAttributes("textStyle").fontSize || "" : "");
		},
	},
	watch: {
		modelValue(val) {
			// External change (e.g. loading a draft) — sync without losing the cursor.
			if (this.editor && val !== this.editor.getHTML()) {
				this.editor.commands.setContent(val || "", false);
			}
		},
	},
	mounted() {
		this.editor = markRaw(
			new Editor({
				content: this.modelValue || "",
				extensions: [
					StarterKit,
					Underline,
					TextStyle,
					FontFamily.configure({ types: ["textStyle"] }),
					FontSize,
					Color,
					Link.configure({ openOnClick: false, autolink: true }),
					TextAlign.configure({ types: ["heading", "paragraph"], defaultAlignment: "right" }),
				],
				editorProps: { attributes: { dir: "rtl", class: "oa-prose", spellcheck: "false" } },
				onUpdate: ({ editor }) => this.$emit("update:modelValue", editor.getHTML()),
				onSelectionUpdate: () => (this.tick += 1),
				onTransaction: () => (this.tick += 1),
			}),
		);
	},
	beforeUnmount() {
		if (this.editor) this.editor.destroy();
	},
	methods: {
		faNum(n) {
			return String(n).replace(/\d/g, (d) => FA_DIGITS[+d]);
		},
		is(name) {
			return (this.tick, this.editor && this.editor.isActive(name));
		},
		isHeading(level) {
			return (this.tick, this.editor && this.editor.isActive("heading", { level }));
		},
		isAlign(a) {
			return (this.tick, this.editor && this.editor.isActive({ textAlign: a }));
		},
		run(cmd) {
			this.editor.chain().focus()[cmd]().run();
		},
		toggleHeading(level) {
			this.editor.chain().focus().toggleHeading({ level }).run();
		},
		setAlign(a) {
			this.editor.chain().focus().setTextAlign(a).run();
		},
		setFont(stack) {
			const c = this.editor.chain().focus();
			stack ? c.setFontFamily(stack).run() : c.unsetFontFamily().run();
		},
		setSize(size) {
			const c = this.editor.chain().focus();
			size ? c.setFontSize(size).run() : c.unsetFontSize().run();
		},
		setColor(color) {
			this.editor.chain().focus().setColor(color).run();
		},
		setLink() {
			const prev = this.editor.getAttributes("link").href || "";
			const url = window.prompt("نشانی پیوند:", prev);
			if (url === null) return;
			if (url === "") {
				this.editor.chain().focus().extendMarkRange("link").unsetLink().run();
				return;
			}
			this.editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
		},
	},
};
</script>

<style scoped>
.oa-editor {
	border: 1px solid var(--outline-soft, #e2e8f0);
	border-radius: 12px;
	overflow: hidden;
	background: var(--surface, #fff);
}
.oa-editor-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 2px;
	padding: 6px 8px;
	border-bottom: 1px solid var(--outline-soft, #e2e8f0);
	background: var(--surface-1, #f8fafc);
}
.oa-tb {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border: none;
	border-radius: 8px;
	background: transparent;
	color: var(--on-variant, #475569);
	cursor: pointer;
}
.oa-tb:hover {
	background: var(--surface-2, #eef2f7);
}
.oa-tb.on {
	background: var(--primary-container, #dbeafe);
	color: var(--on-primary-container, #1e40af);
}
.oa-tb .ico {
	font-size: 19px;
}
.oa-tb-select {
	height: 32px;
	border: 1px solid var(--outline-soft, #e2e8f0);
	border-radius: 8px;
	background: var(--surface, #fff);
	color: var(--on-surface, #0f172a);
	font-family: inherit;
	font-size: 12.5px;
	padding: 0 6px;
	cursor: pointer;
}
.oa-tb-sep {
	width: 1px;
	height: 20px;
	background: var(--outline-soft, #e2e8f0);
	margin: 0 4px;
}
.oa-color {
	position: absolute;
	inset: 0;
	opacity: 0;
	width: 100%;
	height: 100%;
	cursor: pointer;
}
.oa-editor-content :deep(.oa-prose) {
	min-height: 220px;
	max-height: 420px;
	overflow: auto;
	padding: 14px 16px;
	font-size: 14px;
	line-height: 2;
	color: var(--on-surface, #0f172a);
	outline: none;
}
.oa-editor-content :deep(.oa-prose p) {
	margin: 0 0 10px;
}
.oa-editor-content :deep(.oa-prose:focus) {
	outline: none;
}
.oa-editor-content :deep(.ProseMirror-focused) {
	outline: none;
}
</style>
