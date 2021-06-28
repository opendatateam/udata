<template>
    <strong class="author">
    {{
        author.first_name +
        " " +
        author.last_name
    }}
    <span v-if="badge" class="badge ml-sm">{{ $t("Admin") }}</span>
    </strong>
</template>

<script>
export default {
  props: {
    author: Object,
    badge: Boolean
  }
};
</script>
