<template>
    <span class="fr-text--sm fr-mb-0">
    {{
        author.first_name +
        " " +
        author.last_name
    }}
    <span v-if="badge" class="badge ml-sm">{{ $t("Admin") }}</span>
    </span>
</template>

<script>
export default {
  props: {
    author: Object,
    badge: Boolean
  }
};
</script>
