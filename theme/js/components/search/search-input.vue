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
  <section class="search-input fr-grid-row">
      <span class="icon" :class="{ active: queryString }" v-html="icon"></span>
      <input
        class="fr-col w-100 fr-ml-3v"
        type="text"
        name="q"
        :value="queryString"
        @input="_onChange"
        @keydown.delete="onDelete"
        ref="input"
        :aria-label="placeholder || $t('Search...')"
        :placeholder="placeholder || $t('Search...')"
        data-cy="search-input"
      />
  </section>
</template>

<script>
import Icon from "svg/search.svg";

export default {
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
};
</script>
