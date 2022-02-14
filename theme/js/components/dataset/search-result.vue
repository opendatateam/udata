<!-- This is similar to the Jinja2 `dataset/search-result.html` template but in
Vue. -->

<template>
  <article class="dataset-card dataset-search-result py-xs">
    <div class="card-logo" v-if="organization">
      <Placeholder
        type="dataset"
        :src="organization.logo_thumbnail"
        :alt="organization.name"
      />
      <div class="logo-badge logo-badge--bottom-right">
        <span v-html="lock" v-if="private" />
        <span v-html="certified" v-else-if="organizationCertified" />
      </div>
    </div>
    <div class="card-logo" v-else-if="owner">
      <Placeholder
        type="dataset"
        :src="owner.logo_thumbnail"
        :alt="owner.fullname"
      />
    </div>
    <div class="card-logo" v-else>
      <Placeholder type="dataset" />
    </div>
    <div class="card-data">
      <h4 class="card-title">{{ title }}</h4>
      <div class="card-description text-grey-380 mt-xs">
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
      <div v-if="geoZone">
        <dt>{{ $t("Spatial coverage") }}</dt>
        <dd>{{ geoZone.join(", ") }}</dd>
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
import useOrganizationCertified from "../../composables/useOrganizationCertified";
import useGeoZone from "../../composables/useGeoZone";

export default {
  props: {
    title: String,
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
  setup(props) {
    const {organizationCertified} = useOrganizationCertified(props.organization)
    const {geoZone} = useGeoZone(props.spatial)
    return {
      certified,
      lock,
      organizationCertified,
      geoZone,
    };
  }
};
</script>
