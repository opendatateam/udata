<template>
  <button class="fr-btn fr-btn--secondary fr-fi-svg fr-fi--sm fr-btn--icon-left fr-btn--sm" :disabled="loading" @click.prevent="showSchemaModal">
    <span class="fr-grid-row fr-mr-1v" v-html="triangle"></span>
    {{ $t('See schema') }}
  </button>
</template>

<script>
import {inject, defineComponent} from 'vue';
import useSchema from "../../../composables/useSchema";
import triangle from "svg/triangle.svg";

export default defineComponent({
  props: {
    resource: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const { authorizeValidation, documentationUrl, loading, validationUrl} = useSchema(props.resource);
    const showModal = inject('$showModal');
    const showSchemaModal = () => showModal('schema', {
      resourceSchema: props.resource.schema,
      documentationUrl: documentationUrl.value,
      validationUrl: validationUrl.value,
      authorizeValidation: authorizeValidation.value
    });
    return {
      loading,
      authorizeValidation,
      documentationUrl,
      validationUrl,
      showSchemaModal,
      triangle,
    }
  },
});
</script>
