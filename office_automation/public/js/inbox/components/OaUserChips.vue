<template>
	<div class="oa-chips">
		<div class="oa-chips-box" :class="{ focused }" @click="focusInput">
			<TransitionGroup name="oa-slide">
				<span v-for="u in modelValue" :key="u.value" class="oa-chip">
					{{ u.label }}
					<span class="oa-chip-x" @click.stop="remove(u)">
						<OaIcon name="x" :size="13" />
					</span>
				</span>
			</TransitionGroup>
			<input
				ref="input"
				v-model="query"
				class="oa-chips-input"
				:placeholder="modelValue.length ? '' : placeholder"
				@focus="focused = true"
				@blur="onBlur"
				@input="search"
				@keydown.down.prevent="move(1)"
				@keydown.up.prevent="move(-1)"
				@keydown.enter.prevent="choose(suggestions[activeIndex])"
				@keydown.backspace="onBackspace"
			/>
		</div>

		<Transition name="oa-pop">
			<div v-if="focused && suggestions.length" class="oa-suggest">
				<div
					v-for="(s, i) in suggestions"
					:key="s.value"
					class="oa-suggest-item"
					:class="{ active: i === activeIndex }"
					@mousedown.prevent="choose(s)"
					@mouseenter="activeIndex = i"
				>
					<span>{{ s.label }}</span>
					<small>{{ s.value }}</small>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script>
import OaIcon from "./OaIcon.vue";

export default {
	name: "OaUserChips",
	components: { OaIcon },
	props: {
		// modelValue: [{ value: email, label: full name }]
		modelValue: { type: Array, default: () => [] },
		placeholder: { type: String, default: "Type a name…" },
	},
	emits: ["update:modelValue"],
	data() {
		return { query: "", suggestions: [], focused: false, activeIndex: 0, _timer: null };
	},
	methods: {
		focusInput() {
			this.$refs.input && this.$refs.input.focus();
		},
		onBlur() {
			// Delay so a mousedown on a suggestion still registers.
			setTimeout(() => (this.focused = false), 120);
		},
		search() {
			clearTimeout(this._timer);
			const txt = this.query.trim();
			if (!txt) {
				this.suggestions = [];
				return;
			}
			this._timer = setTimeout(async () => {
				try {
					const rows = await frappe.db.get_list("User", {
						fields: ["name", "full_name"],
						filters: [
							["enabled", "=", 1],
							["name", "not in", ["Guest", "Administrator"]],
						],
						or_filters: [
							["full_name", "like", `%${txt}%`],
							["name", "like", `%${txt}%`],
						],
						limit: 8,
					});
					const chosen = new Set(this.modelValue.map((u) => u.value));
					this.suggestions = rows
						.filter((r) => !chosen.has(r.name))
						.map((r) => ({ value: r.name, label: r.full_name || r.name }));
					this.activeIndex = 0;
				} catch (e) {
					this.suggestions = [];
				}
			}, 180);
		},
		move(delta) {
			if (!this.suggestions.length) return;
			this.activeIndex =
				(this.activeIndex + delta + this.suggestions.length) % this.suggestions.length;
		},
		choose(s) {
			if (!s) return;
			this.$emit("update:modelValue", [...this.modelValue, s]);
			this.query = "";
			this.suggestions = [];
			this.$nextTick(this.focusInput);
		},
		remove(u) {
			this.$emit(
				"update:modelValue",
				this.modelValue.filter((x) => x.value !== u.value)
			);
		},
		onBackspace() {
			if (!this.query && this.modelValue.length) {
				this.remove(this.modelValue[this.modelValue.length - 1]);
			}
		},
	},
};
</script>
