<template>
  <div class="avatar">
    <img :src="avatarUrl" loading="lazy" alt="" />
  </div>
</template>

<script>
import useUserAvatar from "../../composables/useUserAvatar";

export default {
  props: {
    user: Object,
    size: {
      type: Number,
      default: 40,
    },
  },
  setup(props) {
    const avatarUrl = useUserAvatar(props.user, props.size);
    return {
      avatarUrl
    }
  },
};
</script>
