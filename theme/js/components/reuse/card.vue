<!-- This is similar to the Jinja2 `reuse/card.html` template but in
Vue and simpler -->

<template>
  <article class="reuse-card text-align-center fr-text--sm fr-mb-0">
    <Placeholder
      class="reuse-image fr-mb-3v fr-responsive-img"
      alt=""
      :src="image_url"
      type="reuse"
    />
    <div>
      {{ type_label }}
    </div>
    <div>
      {{ title }}
      <span class="badge grey-300 fr-ml-1w" v-if="private">{{ $t('Private') }}</span>
    </div>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";

export default {
  props: {
    title: String,
    image_url: String,
    type_label: String,
    metrics: Object,
    datasets: {
      type: Number,
      default: 0,
    },
    private: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    Placeholder,
  }
};
</script>
