<template>
  <ContentLoader
    :width="350"
    :height="180"
    :speed="2"
    primaryColor="#f3f3f3"
    secondaryColor="#ecebeb"
  >
    <rect x="43" y="153" rx="3" ry="3" width="97" height="6" />
    <rect x="44" y="166" rx="3" ry="3" width="97" height="5" />
    <rect x="184" y="7" rx="5" ry="5" width="130" height="130" />
    <rect x="198" y="153" rx="3" ry="3" width="97" height="6" />
    <rect x="199" y="166" rx="3" ry="3" width="97" height="5" />
    <rect x="27" y="8" rx="5" ry="5" width="130" height="130" />
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
