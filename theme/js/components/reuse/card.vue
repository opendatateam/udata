<!-- This is similar to the Jinja2 `reuse/card.html` template but in
Vue and simpler -->

<template>
  <article class="reuse-card">
    <Placeholder
      class="reuse-image mb-sm"
      :alt="title"
      backgroundImage
      :src="image_url"
      type="reuse"
    />
    <div class="reuse-info">
      <div class="reuse-info-type fs-xs">
        {{ type_label }}
      </div>
      <div class="reuse-info-amount fs-xs text-grey-380 mb-xs"></div>
      <div class="reuse-info-title h4">
        {{ title }}
      </div>
    </div>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";
import icon from "svg/actions/star.svg";

export default {
  created() {
    this.icon = icon;
  },
  props: {
    title: String,
    image_url: String,
    type_label: String,
    metrics: Object,
    datasets: Number,
  },
  components: {
    Placeholder,
  },
};
</script>
