<template>
  <article class="dataset-card compact">
    <div class="card-logo">
      <Placeholder type="reuse" :src="image_url" :alt="title" />
      <div class="logo-badge">
        <span v-html="privateIcon" v-if="private" />
        <span v-html="certified" v-else-if="organization?.public_service" />
      </div>
    </div>
    <div class="card-data">
      <h4 class="card-body">
        {{ title }}
      </h4>
      <div class="card-footer">
        <ul class="card-features fs-xs"></ul>
      </div>
    </div>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";
import certified from "svg/certified.svg";
import privateIcon from "svg/private.svg";

export default {
  created() {
    this.certified = certified;
    this.privateIcon = privateIcon;
  },
  props: {
    title: String,
    image_url: String,
    organization: Object,
    private: Boolean,
  },
  components: {
    Placeholder,
  },
};
</script>
