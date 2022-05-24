<!--
---
name: Input
category: Search
---

# Search input

It's an input that calls the passed `onChange` function on each change.
You can also pass it a `value` prop that will populate the field.
If the submitUrl prop is passed, it will redirect on Submit.
-->

<template>
  <section class="fr-search-bar fr-search-bar--lg w-100">
    <input
      type="search"
      name="q"
      :value="queryString"
      @input="_onChange"
      @keydown.delete="onDelete"
      ref="input"
      class="fr-input"
      :aria-label="placeholder || $t('Search...')"
      :placeholder="placeholder || $t('Search...')"
      data-cy="search-input"
    />
    <button class="fr-btn" :title="$t('Search')" type="submit">
      {{ $t('Search') }}
    </button>
  </section>
</template>

<script>
import Icon from "svg/search.svg";
import { defineComponent } from "vue";

export default defineComponent({
  created() {
    this.icon = Icon;
    this.queryString = this.value;
  },
  watch: {
    value: function (val) {
      this.queryString = val;
    },
  },
  async mounted() {
    //this.$nextTick doesn't work because of browsers®
    setTimeout(() => this.focus(), 100);
  },
  props: {
    onChange: Function,
    value: String,
    placeholder: String,
  },
  data() {
    return {
      queryString: "",
    };
  },
  methods: {
    _onChange(e) {
      if (this.onChange) this.onChange(e.target.value);
    },
    onDelete() {
      if (this.queryString === "") this.onChange(this.queryString);
    },
    focus() {
      this.$refs.input.focus({
        preventScroll: true,
      });
    }
  },
});
</script>
