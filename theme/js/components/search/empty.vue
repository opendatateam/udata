<!--
Nothing to see here ! Well actually it's a small component that says this.
-->

<template>
  <div
    class="search-empty bg-grey-50 p-lg my-md pb-hg"
    :class="{ 'row-inline': wide }"
  >
    <div :class="{ 'pr-lg': wide }" v-html="Empty" />
    <div :class="{ 'mt-lg': !wide }">
      <h4>
        {{ $t("There are no results for your search") }}
      </h4>
      <p>
        {{ copy }}
        <span v-if="queryString">{{ `"${queryString}"` }}</span>
      </p>
      <p v-if="copyAfter">{{ copyAfter }}</p>
      <button class="nav-link" @click="onClick" v-if="onClick">{{ cta }}</button>
      <a class="nav-link" :href="link" v-else>{{ cta }}</a>
    </div>
  </div>
</template>

<script>
import Empty from "svg/search/empty.svg";

export default {
  props: {
    queryString: String,
    cta: String,
    copy: String,
    copyAfter: String,
    link: String,
    onClick: Function,
    wide: Boolean,
  },
  data() {
    return {
      Empty,
    };
  },
};
</script>
