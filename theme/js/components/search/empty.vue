<!--
Nothing to see here ! Well actually it's a small component that says this.
-->

<template>
  <div class="search-empty bg-grey-50 p-lg my-md pb-hg" :class="wide && 'row-inline'">
    <div :class="wide && 'pr-lg'" v-html="Empty" />
    <div :class="!wide && 'mt-lg'">
      <h4>
        {{ $t("@@Aucun résultat ne correspond à votre recherche") }}
      </h4>
      <p>
        {{ copy }}
        "{{ queryString }}"
      </p>
      <p v-if="copyAfter">{{ copyAfter }}</p>
      <a class="nav-link mt-md" @click="onClick" v-if="onClick">{{ cta }}</a>
      <a class="nav-link mt-md" :href="link" v-else>{{ cta }}</a>
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
    wide: Boolean
  },
  data() {
    return {
      Empty,
    };
  },
};
</script>
