<template>
    <search-box v-if="active"></search-box>
</template>

<script>
import SearchBox from "./search-box";

export default {
  components: {
    SearchBox,
  },
  data() {
    return {
      active: true,
    };
  },
  methods: {
      trigger() {
          this.active = !this.active
      }
  },
};
</script>
