<template>
  <ContentLoader
    :width="280"
    :height="180"
    :speed="2"
    primaryColor="#7c7c7c"
    secondaryColor="#2d2d2d"
  >
    <rect x="104" y="41" rx="3" ry="3" width="162" height="10" />
    <rect x="105" y="63" rx="3" ry="3" width="139" height="5" />
    <rect x="26" y="99" rx="5" ry="5" width="60" height="60" />
    <rect x="104" y="113" rx="3" ry="3" width="162" height="10" />
    <rect x="105" y="135" rx="3" ry="3" width="139" height="5" />
    <rect x="26" y="24" rx="5" ry="5" width="60" height="60" />
  </ContentLoader>
</template>

<script>
import { ContentLoader } from "vue-content-loader";

export default {
  components: {
    ContentLoader,
  },
};
</script>
