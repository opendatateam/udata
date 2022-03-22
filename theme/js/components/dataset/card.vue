<template>
  <article class="dataset-card compact">
    <div class="card-logo">
      <Placeholder type="reuse" :src="image_url" alt="" />
    </div>
    <div class="card-data">
      <h3 class="card-body h4">
        {{ title }}
      </h3>
      <div class="card-footer">
        <ul class="card-features fs-xs"></ul>
      </div>
    </div>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";

export default {
  components: {
    Placeholder,
  },
  props: {
    title: String,
    image_url: String,
  },
};
</script>
