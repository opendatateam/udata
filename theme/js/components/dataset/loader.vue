<template>
  <ContentLoader
    :width="280"
    :height="180"
    :speed="2"
    primaryColor="#f3f3f3"
    secondaryColor="#ecebeb"
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
import { defineComponent } from "vue";
import { ContentLoader } from "vue-content-loader";

export default defineComponent({
  components: {
    ContentLoader,
  },
});
</script>
