<template>
  <article class="fr-pt-5v fr-pb-6v fr-px-1w border-bottom border-default-grey fr-enlarge-link">
    <div class="fr-grid-row fr-grid-row--gutters fr-grid-row--top">
      <div class="fr-col-auto">
          <div class="logo">
            <Placeholder
              v-if="organization"
              type="dataset"
              :src="organization.logo_thumbnail"
              :alt="organization.name"
              :size="60"
            />
            <Avatar
              v-else-if="owner"
              :user="owner"
              :size="60"
            />
            <Placeholder
              v-else
              type="dataset"
            />
          </div>
        </div>
      <div class="fr-col">
          <h4 class="fr-mb-1v">
            <a :href="page" class="text-grey-500">
              {{ title }}
              <small v-if="acronym">{{ acronym }}</small>
            </a>
            <span
              v-if="private"
              class="badge grey-300 fr-ml-1w"
            >
              {{ $t('Private') }}
            </span>
          </h4>
          <p class="fr-m-0 not-enlarged" v-if="organization || owner">
            {{ $t('From') }} 
            <a v-if="organization" :href="organization.page">
                <OrganizationNameWithCertificate :organization="organization" />
            </a>
            <template v-if="owner">{{ownerName}}</template>
          </p>
          <p class="fr-mt-1w fr-mb-2w fr-hidden fr-unhidden-sm">
            {{ $filters.excerpt(description, 160) }}
          </p>
          <p class="fr-mb-0 text-mention-grey">
            <template v-if="!externalSource">
              {{ $t('Updated on {date}', {date: $filters.formatDate(last_modified)}) }}
                <span v-if="license" class="fr-hidden inline-sm">
                  &mdash;
                </span>
            </template>
            <span v-if="license" class="fr-hidden inline-sm">
              <span class="not-enlarged" v-if="license.url">
                <a :href="license.url" class="text-decoration-underline text-decoration-underline--dsfr text-mention-grey">
                  {{license.title}}
                </a>
              </span>
              <template v-else>
                {{license.title}}
              </template>
            </span>
          </p>
        </div>
      <ul class="fr-hidden fr-unhidden-sm fr-hidden-md fr-unhidden-lg fr-col-auto fr-tags-group fr-grid-row--bottom self-center flex-direction-column">
            <li>
              <span class="fr-tag">
                <i18n-t keypath="{n} reuses" :plural="metrics.reuses || 0" scope="global">
                  <template #n>
                    <strong class="fr-mr-1v">{{metrics.reuses || 0}}</strong>
                  </template>
                </i18n-t>
                </span>
            </li>
            <li>
              <span class="fr-tag">
                <i18n-t keypath="{n} favorites" :plural="metrics.followers || 0" scope="global">
                  <template #n>
                    <strong class="fr-mr-1v">{{metrics.followers}}</strong>
                  </template>
                </i18n-t>
              </span>
            </li>
        </ul>
    </div>
  </article>
</template>

<script>
import { defineComponent, computed, ComputedRef } from "vue";
import lock from "bundle-text:svg/private.svg";
import useLicense from "../../composables/useLicense";
import useOwnerName from "../../composables/useOwnerName";
import useExternalSource from "../../composables/useExternalSource";
import Avatar from "../discussions/avatar.vue";
import OrganizationNameWithCertificate from "../organization/organization-name-with-certificate.vue";
import Placeholder from "../utils/placeholder.vue";

export default defineComponent({
  inheritAttrs: false,
  props: {
    acronym: String,
    description: {
      type: String,
      required: true,
    },
    extras: {
      type: Object,
    },
    last_modified: {
      type: Date,
      required: true,
    },
    license: {
      type: String,
      required: true,
    },
    metrics: Object,
    organization: Object,
    owner: Object,
    page: {
      type: String,
      required: true,
    },
    private: Boolean,
    resources: Object,
    title: {
      type: String,
      required: true,
    },
  },
  components: {
    Avatar,
    OrganizationNameWithCertificate,
    Placeholder,
  },
  setup(props) {
    /** @type {ComputedRef<import("../../composables/useOwnerName").Owned>} */
    const owned = computed(() => {
      let owned = {};
      if(props.organization) {
        owned.organization = props.organization;
      }
      if(props.owner) {
        owned.owner = props.owner;
      }
      return owned;
    });
    const ownerName = useOwnerName(owned);
    const license = useLicense(props.license);
    const externalSource = useExternalSource(props.extras);
    return {
      externalSource,
      license,
      lock,
      ownerName,
    };
  }
});
</script>
