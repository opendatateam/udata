<template>
  <button class="fr-btn btn-primary" @click.prevent="showModal">
      {{$t('See schema')}}
  </button>
</template>

<script>
import config from "../../../config";
export default {
  props: {
    resource: {
      type: Object,
      required: true
    }
  },
  computed: {
    schema() {
      return this.schemas.find(schema => schema.name === this.resource.schema.name);
    },
    authorizeValidation() {
      return this.schema && this.schema.schema_type === 'tableschema';
    },
    documentationUrl() {
      return `https://schema.data.gouv.fr/${this.resource.schema.name}/latest.html`;
    },
    validationUrl() {
      if(!this.authorizeValidation) {
        return null;
      }
      let schemaPath = {'schema_name': `schema-datagouvfr.${this.resource.schema.name}`};
      if(this.resource.schema.version) {
        const versionUrl = this.schema.versions.find(version => version.version_name === this.resource.schema.version)?.schema_url;
        schemaPath = {"schema_url": versionUrl};
      }
      const query = new URLSearchParams({
        'input': 'url',
        'url': this.resource.url,
        ...schemaPath,
      }).toString();
      return `${config.schema_validata_url}/table-schema?${query}`;
    }
  },
  data() {
    return {
      loading: false,
      schemas: [],
    }
  },
  created() {
    this.loading = true;
    this.$getSchemaCatalog().then(schemas => this.schemas = schemas).finally(() => this.loading = false);
  },
  methods: {
    showModal() {
      return this.$showModal('schema', {
        resourceSchema: this.resource.schema,
        documentationUrl: this.documentationUrl,
        validationUrl: this.validationUrl,
        authorizeValidation: this.authorizeValidation
      });
    }
  }
}
</script>
