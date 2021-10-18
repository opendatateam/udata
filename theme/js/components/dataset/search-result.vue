<!-- This is similar to the Jinja2 `dataset/search-result.html` template but in
Vue. -->

<template>
  <article class="dataset-card dataset-search-result">
    <div class="card-logo" v-if="organization">
      <Placeholder
        type="dataset"
        :src="organization.logo_thumbnail"
        :alt="organization.name"
      />
    </div>
    <div class="card-logo" v-else-if="owner">
      <Placeholder
        type="dataset"
        :src="owner.logo_thumbnail"
        :alt="owner.fullname"
      />
      <div class="logo-badge">
        <span v-html="lock" v-if="private" />
        <span v-html="certified" v-else-if="organization?.public_service" />
      </div>
    </div>
    <div class="card-logo" v-else>
      <Placeholder type="dataset" />
    </div>
    <div class="card-data">
      <h4 class="card-title">{{ title }}</h4>
      <div class="card-description text-grey-300 mt-xs">
        {{ $filters.excerpt(description) }}
      </div>
    </div>
    <dl class="card-hover">
      <div v-if="temporal_coverage">
        <dt>{{ $t("Temporal coverage") }}</dt>
        <dd>{{ temporal_coverage.start + " - " + temporal_coverage.end }}</dd>
      </div>
      <div v-if="frequency">
        <dt>{{ $t("Frequency") }}</dt>
        <dd>{{ frequency }}</dd>
      </div>
      <div v-if="geozone">
        <dt>{{ $t("Spatial coverage") }}</dt>
        <dd>{{ geozone.join(", ") }}</dd>
      </div>
      <div v-if="spatial?.granularity">
        <dt>{{ $t("Territorial coverage granularity") }}</dt>
        <dd>{{ spatial.granularity }}</dd>
      </div>
    </dl>
    <ul class="card-footer">
      <li>
        <strong>{{ resources.length || 0 }}</strong>
        {{ $tc("resources", resources.length || 0) }}
      </li>
      <li>
        <strong>{{ metrics.reuses || 0 }}</strong>
        {{ $tc("reuses", metrics.reuses || 0) }}
      </li>
      <li>
        <strong>{{ metrics.followers || 0 }}</strong>
        {{ $tc("favourites", metrics.followers || 0) }}
      </li>
    </ul>
  </article>
</template>

<script>
import Placeholder from "../utils/placeholder";
import certified from "svg/certified.svg";
import lock from "svg/private.svg";

export default {
  props: {
    title: String,
    image_url: String,
    organization: Object,
    owner: Object,
    description: String,
    temporal_coverage: Object,
    frequency: String,
    spatial: Object,
    metrics: Object,
    resources: Array,
    private: Boolean,
  },
  components: {
    Placeholder,
  },
  data() {
    return {
      geozone: null,
    };
  },
  async mounted() {
    this.certified = certified;
    this.lock = lock;
    //Fetching geozone names on load (they're not included in the dataset object)

    const zones = this?.spatial?.zones;
    if (zones) {
      let promises = zones.map((zone) =>
        this.$api
          .get("spatial/zone/" + zone)
          .then((resp) => resp.data)
          .then((obj) => obj && obj?.properties?.name)
      );

      this.geozone = await Promise.all(promises);
    }
  },
};
</script>
