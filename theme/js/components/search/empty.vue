<template>
  <div class="search-empty bg-grey-50 p-lg my-md pb-hg">
    <div v-html="Empty" />
    <h4 class="mt-lg">
      {{ $t("@@Aucun résultat ne correspond à votre recherche") }}
    </h4>
    <p>
      {{ copy }}
      "{{ queryString }}"
    </p>
    <a class="nav-link mt-md" :href="link">{{ cta }}</a>
  </div>
</template>

<script>
import Empty from "svg/search/empty.svg";

export default {
  props: {
    queryString: String,
    cta: String,
    copy: String,
    link: String
  },
  data() {
    return {
      Empty,
    };
  },
};
</script>
