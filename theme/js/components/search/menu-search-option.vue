<template>
  <a class="fr-nav__link unstyled" :href="link">
    <div class="fr-grid-row fr-grid-row--middle">
      <div aria-hidden="true" class="fr-col-auto fr-mr-2w" v-html="icon">
      </div>
      <i18n-t keypath="Search X in Y" class="fr-col" tag="div" scope="global" v-if="query">
        <template #query>
          <em>{{query}}</em>
        </template>
        <template #type>
          <strong>{{type}}</strong>
        </template>
      </i18n-t>
      <i18n-t keypath="Start typing to search in X" class="fr-col" tag="div" scope="global" v-else>
        <template #type>
          <strong>{{type}}</strong>
        </template>
      </i18n-t>
      <div aria-hidden="true" class="fr-col-auto">
        <span class="fr-icon-arrow-right-s-line fr-icon--sm" aria-hidden="true"></span>
      </div>
    </div>
  </a>
</template>

<script>
import {defineComponent} from "vue";
export default defineComponent({
  props: {
    icon: {
      type: String,
      required: true,
    },
    query: {
      type: String,
      required: true,
    },
    link: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      required: true,
    },
  }
});
</script>

<style scoped>

</style>
