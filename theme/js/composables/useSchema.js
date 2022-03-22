import {useI18n} from 'vue-i18n'
import {ref, computed} from "vue";
import getCatalog from "../api/schemas";
import config from "../config";
import {useToast} from "./useToast";

/**
 *
 * @param {ResourceModel} resource
 * @returns {{documentationUrl: Ref<string>, authorizeValidation: Ref<boolean>, name: Ref<?string>, validationUrl: Ref<string>, loading: Ref<boolean>}}
 */
export default function useSchema(resource) {
  const { t } = useI18n();
  const toast = useToast();
  /** @type {Ref<boolean>} */
  const loading = ref(true);
  /** @type {Ref<Array<Schema>>} */
  const schemas = ref([]);
  getCatalog()
    .then(catalog => schemas.value = catalog)
    .catch(() => {
      toast.error(
        t("An error occurred while fetching schemas")
      );
    }).finally(() => loading.value = false);

  /** @type {Ref<?Schema>} */
  const schema = computed(() => schemas.value.find(schema => schema.name === resource.schema.name));

  /** @type {Ref<boolean>} */
  const authorizeValidation = computed(() => !!schema.value && schema.value.schema_type === 'tableschema');

  /** @type {Ref<string>} */
  const documentationUrl = computed(() => `https://schema.data.gouv.fr/${resource.schema.name}/latest.html`);

  /** @type {Ref<string>} */
  const validationUrl = computed(() => {
    if(!authorizeValidation) {
      return null;
    }
    let schemaPath = {'schema_name': `schema-datagouvfr.${resource.schema.name}`};
    if(resource.schema.version) {
      const versionUrl = schema.value.versions.find(version => version.version_name === resource.schema.version)?.schema_url;
      schemaPath = {"schema_url": versionUrl};
    }
    const query = new URLSearchParams({
      'input': 'url',
      'url': resource.url,
      ...schemaPath,
    }).toString();
    return `${config.schema_validata_url}/table-schema?${query}`;
  });

  return {
    authorizeValidation,
    documentationUrl,
    loading,
    validationUrl,
  }
}
