<!--
---
name: Input
category: Suggest
---

# Search input

It's an input that calls the passed `onChange` function on each change.
You can also pass it a `queryString` prop that will populate the field.
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
        v-model="queryString"
        @input="_onChange"
        @keydown.delete="onDelete"
        ref="input"
        :aria-label="$t('Search...')"
        :placeholder="$t('Search...')"
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
  async mounted() {
    //this.$nextTick doesn't work because of browsers®
    setTimeout(() => this.focus(), 100);
  },
  props: {
    onChange: Function,
    value: String,
  },
  data() {
    return {
      queryString: "",
    };
  },
  methods: {
    _onChange() {
      if (this.onChange) this.onChange(this.queryString);
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
