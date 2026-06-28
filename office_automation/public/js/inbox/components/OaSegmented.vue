<template>
	<div class="oa-segmented" role="radiogroup">
		<button
			v-for="opt in options"
			:key="opt.value"
			type="button"
			role="radio"
			:aria-checked="modelValue === opt.value"
			class="oa-seg"
			:class="[{ active: modelValue === opt.value }, opt.tone ? 'tone-' + opt.tone : '']"
			@click="select(opt.value)"
		>
			<OaIcon v-if="opt.icon" :name="opt.icon" :size="15" />
			{{ opt.label }}
		</button>
	</div>
</template>

<script>
import OaIcon from "./OaIcon.vue";

export default {
	name: "OaSegmented",
	components: { OaIcon },
	props: {
		modelValue: { type: String, default: "" },
		// options: [{ value, label, icon?, tone? }]
		options: { type: Array, required: true },
	},
	emits: ["update:modelValue"],
	methods: {
		select(value) {
			// Only emit on an actual change — re-clicking the active option must not
			// fire an update (which would, e.g., silently reset an edited date).
			if (value !== this.modelValue) this.$emit("update:modelValue", value);
		},
	},
};
</script>
