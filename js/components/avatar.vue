<template>
  <a class="avatar" :href="user.url" :title="user | display">
      <img v-if="user.avatar" :src="user.avatar"
          class="avatar" :alt="user | display" :width="size" :height="size">
  </a>
</template>

<script>
export cont DEFAULT_SIZE = 52;

export default {
    props: {
        user: Object,
        size: {
            type: Number,
            default: DEFAULT_SIZE
        }
    }
}
</script>
