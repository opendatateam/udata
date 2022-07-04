<template>
  {{ organization.name }} 
  <span
    v-if="organizationCertified"
    v-html="certified"
    class="fr-icon-svg fr-icon--sm"
    :title="$t('The identity of this public service is certified by {certifier}', { certifier: title })"
  >
  </span>
</template>

<script>
import { defineComponent } from "vue";
import certified from "bundle-text:svg/certified.svg";
import { title } from "../../config";
import useOrganizationCertified from "../../composables/useOrganizationCertified";

export default defineComponent({
  props: {
    organization: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const { organizationCertified } = useOrganizationCertified(props.organization);
    return {
      certified,
      organizationCertified,
      title,
    };
  },
});
</script>
