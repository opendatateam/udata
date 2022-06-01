<template>
  <a
    :href="adminUrl"
    :title="$t('Edit resource')"
    class="fr-btn fr-btn--secondary fr-btn--secondary-grey-500 fr-btn--sm fr-icon-svg"
    v-html="edit"
    >
  </a>
</template>

<script>
import edit from "bundle-text:svg/edit.svg";
import config from "../../../config";

export default {
  name: "edit-button",
  props: {
    datasetId: {
      type: String,
      required: true,
    },
    isCommunityResource: {
      type: Boolean,
      default: false,
    },
    resourceId: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const resourceType = props.isCommunityResource ? 'community-resource' : 'resource';
    const adminUrl = `${config.admin_root}dataset/${props.datasetId}/${resourceType}/${props.resourceId}`;
    return {
      adminUrl,
      edit
    }
  }
}
</script>

<style scoped>

</style>
