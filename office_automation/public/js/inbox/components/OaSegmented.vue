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
			@click="$emit('update:modelValue', opt.value)"
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
};
</script>
