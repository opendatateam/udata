import {computed} from "vue";
import config from "../config";

/**
 *
 * @param {Ref<string>} q
 * @returns {{datasetUrl, organizationUrl, reuseUrl}}
 */
export default function useSearchUrl(q) {
  const datasetUrl = computed(() => `${config.values.datasetUrl}?q=${q.value}`);
  const organizationUrl = computed(() => `${config.values.organizationUrl}?q=${q.value}`);
  const reuseUrl = computed(() => `${config.values.reuseUrl}?q=${q.value}`);
  return {
    datasetUrl,
    organizationUrl,
    reuseUrl,
  }
}
