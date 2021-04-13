<!--
---
name: Input
category: Suggest
---

# Search input

It's an input that calls the passed `onChange` function on each change.
You can also pass it a `value` prop that will populate the field.
-->

<template>
  <section class="search-input">
    <form action="" @submit.prevent="onSubmit" class="row-inline">
      <span
        class="icon"
        :class="{ active: queryString }"
        v-html="icon"
        width="32"
      />
      <input
        type="text"
        :value="queryString"
        @input="_onChange"
        @keydown.delete="onDelete"
        ref="input"
        :aria-label="placeholder || $t('Search...')"
        :placeholder="placeholder || $t('Search...')"
      />
    </form>
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
    value: function(val) {
      this.queryString = val
    }
  },
  async mounted() {
    //this.$nextTick doesn't work because of browsers®
    setTimeout(() => this.focus(), 100);
  },
  props: {
    onChange: Function,
    value: String,
    placeholder: String
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
    },
  },
};
</script>
