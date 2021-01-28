<template>
  <article class="dataset-card no-border">
    <div class="card-logo">
      <Placeholder type="reuse" :src="image_url" :alt="title" />
    </div>
    <div class="card-data">
      <h4 class="card-body">
        {{ title }}
      </h4>
      <div class="card-footer">
        <ul class="card-features fs-xs">
          <li>252 ressources</li>
          <li>2 réutilisations</li>
        </ul>
      </div>
    </div>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";

export default {
    props: {
        title: String,
        image_url: String,
    },
    components: {
        Placeholder
    }
};
</script>
