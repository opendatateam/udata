<template>
  <form class="fr-pt-3v" @submit.prevent="search">
    <div class="fr-grid-row fr-grid-row--middle justify-between search-bar" ref="searchRef">
      <SearchInput
        :onChange="handleSearchChange"
        :value="queryString"
        :placeholder="$t('Ex. 2022 presidential election')"
      />
    </div>
    <div class="fr-grid-row fr-mt-1w fr-mt-md-5v">
      <div class="fr-col-12 fr-col-md-4 fr-col-lg-3">
        <nav class="fr-sidemenu" :aria-label="$t('Filter results')">
          <div class="fr-sidemenu__inner">
            <button class="fr-sidemenu__btn fr-mt-1w" hidden aria-controls="fr-sidemenu-wrapper" aria-expanded="false">{{$t('Filter results')}}</button>
            <div class="fr-collapse" id="fr-sidemenu-wrapper">
              <div class="fr-sidemenu__title fr-mb-3v">{{$t('Filters')}}</div>
              <div class="fr-grid-row fr-grid-row--gutters">
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Organizations')"
                    :searchPlaceholder="$t('Search an organization...')"
                    :allOption="$t('All organizations')"
                    listUrl="/organizations/?sort=-followers"
                    suggestUrl="/organizations/suggest/"
                    entityUrl="/organizations/"
                    :values="facets.organization"
                    :onChange="handleFacetChange('organization')"
                  />
                </div>
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Tags')"
                    :searchPlaceholder="$t('Search a tag...')"
                    :allOption="$t('All tags')"
                    suggestUrl="/tags/suggest/"
                    :values="facets.tag"
                    :onChange="handleFacetChange('tag')"
                    :minimumCharacterBeforeSuggest="2"
                  />
                </div>
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Formats')"
                    :searchPlaceholder="$t('Search a format...')"
                    :allOption="$t('All formats')"
                    listUrl="/datasets/extensions/"
                    :values="facets.format"
                    :onChange="handleFacetChange('format')"
                  />
                </div>
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Licenses')"
                    :explanation="$t('Licenses define reuse rules for published datasets. See page data.gouv.fr/licences')"
                    :searchPlaceholder="$t('Search a license...')"
                    :allOption="$t('All licenses')"
                    listUrl="/datasets/licenses/"
                    :values="facets.license"
                    :onChange="handleFacetChange('license')"
                  />
                </div>
                <div class="fr-col-12">
                  <SchemaFilter
                    :values="facets.schema"
                    :onChange="handleFacetChange('schema')"
                  />
                </div>
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Spatial coverage')"
                    :explanation="$t('Geographic areas covered by data and for which they are relevant.')"
                    :searchPlaceholder="$t('Search a spatial coverage...')"
                    :allOption="$t('All coverages')"
                    suggestUrl="/spatial/zones/suggest/"
                    entityUrl="/spatial/zone/"
                    :values="facets.geozone"
                    :onChange="handleFacetChange('geozone')"
                  />
                </div>
                <div class="fr-col-12">
                  <MultiSelect
                    :placeholder="$t('Spatial granularity')"
                    :explanation="$t('Finest level of geographic detail covered by data.')"
                    :searchPlaceholder="$t('Search a granularity...')"
                    :allOption="$t('All granularities')"
                    listUrl="/spatial/granularities/"
                    :values="facets.granularity"
                    :onChange="handleFacetChange('granularity')"
                  />
                </div>
                <div class="fr-col-12 fr-mb-3w">
                  <button
                    class="fr-btn fr-btn--secondary fr-icon-close-circle-line fr-btn--icon-left"
                    @click="resetFilters"
                    v-if="isFiltered"
                  >
                    {{$t('Reset filters')}}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </nav>
      </div>
      <section class="fr-col-12 fr-col-md-8 fr-col-lg-9 fr-mt-2w fr-mt-md-0 search-results" ref="resultsRef" v-bind="$attrs">
        <div class="fr-grid-row fr-grid-row--gutters fr-grid-row--middle justify-between fr-pb-1w">
          <p class="fr-col-auto fr-my-0" v-if="totalResults">
            {{ $t("X Results", totalResults) }}
          </p>
          <div class="fr-col-auto fr-grid-row fr-grid-row--middle">
            <label for="sort-search" class="fr-col-auto fr-text--sm fr-m-0 fr-mr-1w">
                {{$t('Sort by:')}}
            </label>
            <div class="fr-col">
                <select
                  id="sort-search"
                  class="fr-select"
                  name="sort"
                  v-model="searchSort"
                  @change="handleSortChange"
                >
                  <option value="">
                    {{$t('Relevance')}}
                  </option>
                  <option v-for="{value, label} in sortOptions" :value='value'>
                    {{label}}
                  </option>
                </select>
            </div>
          </div>
        </div>
        <transition mode="out-in">
          <div v-if="loading">
            <Loader />
          </div>
          <ul v-else-if="results.length" class="fr-mt-1w border-default-grey border-top">
            <li v-for="result in results" :key="result.id">
              <a :href="result.page" class="unstyled fr-raw-link w-10 block">
                <Dataset v-bind="result" />
              </a>
            </li>
            <Pagination
              v-if="totalResults > pageSize"
              :page="currentPage"
              :pageSize="pageSize"
              :totalResults="totalResults"
              :changePage="changePage"
              class="fr-mt-2w"
            />
          </ul>
          <div v-else>
            <Empty
              wide
              :queryString="queryString"
              :cta="$t('Reset filters')"
              :copy="$t('No dataset matching your query')"
              :copyAfter="
                $t('You can try to reset the filters to expand your search.')
              "
              :onClick="() => resetForm()"
            />
          </div>
        </transition>
      </section>
    </div>
  </form>
</template>

<script>
import { defineComponent, ref, Ref, onMounted, computed, watch, PropType } from "vue";
import {useI18n} from 'vue-i18n';
import axios from "axios";
import { CancelTokenSource } from "axios";
import { generateCancelToken, apiv2 } from "../../plugins/api";
import {useToast} from "../../composables/useToast";
import useSearchUrl from "../../composables/useSearchUrl";
import SearchInput from "./search-input.vue";
import Dataset from "../dataset/search-result.vue";
import Loader from "../dataset/loader.vue";
import SchemaFilter from "./schema-filter.vue";
import Empty from "./empty.vue";
import Pagination from "../pagination/pagination.vue";
import MultiSelect from "./multi-select.vue";

export default defineComponent({
  components: {
    MultiSelect,
    SearchInput,
    SchemaFilter,
    Dataset,
    Empty,
    Loader,
    Pagination,
  },
  props: {
    disableFirstSearch: {
      type: Boolean,
      default: false,
    },
    sorts: {
      /** @type {PropType<Array<{label: string, order: string, value: string}>>} */
      type: Array,
      default: [],
    }
  },
  setup(props) {
    const { t } = useI18n();
    const toast = useToast();
    /**
     * Update search params from URL on page load for deep linking
     */
    const url = new URL(window.location.href);
    const params = new URLSearchParams(url.search);
    
    /**
     * Search query
     */
    const queryString = ref('');

    /**
     * Reuse url of the query
     */
    const {reuseUrl} = useSearchUrl(queryString);

    /**
     * Query sort
     */
    const searchSort = ref('');

    /**
     * Search results
     */
    const results = ref([]);

    /**
     * Count of search results
     */
    const totalResults = ref(0);

    /**
     * Current page of results
     */
    const currentPage = ref(1);

    /**
     * Search page size
     */
    const pageSize = 20;

    /**
     * All other params are kept here as facets
     */
    const facets = ref({});

    /**
     * Search loading state
     */
    const loading = ref(false);

    /**
     * Current request if any to be cancelled if a new one comes
     * @type {Ref<CancelTokenSource | null>}
     */
    const currentRequest = ref(null);

    /**
     * Vue ref to results HTML
     * @type {Ref<HTMLElement | null>}
     */
    const resultsRef = ref(null);

    /**
     * Vue ref to results HTML
     * @type {Ref<HTMLElement | null>}
     */
    const searchRef = ref(null);

    /**
     * Search new dataset results
     */
    const search = () => {
      loading.value = true;
      if (currentRequest.value) currentRequest.value.cancel();
      currentRequest.value = generateCancelToken();
      apiv2
        .get("/datasets/search/", {
          cancelToken: currentRequest.value.token,
          params: {
            ...paramUrl.value,
            page_size: pageSize,
          },
        })
        .then((res) => res.data)
        .then((result) => {
          results.value = result.data;
          totalResults.value = result.total;
          loading.value = false;
        })
        .catch((error) => {
          if (!axios.isCancel(error)) {
            toast.error(t("Error getting search results."));
            loading.value = false;
          }
        });
    }

    /**
     * Called when user type in search field
     * @param {string} input - input typed by user
     */
    const handleSearchChange = (input) => {
      queryString.value = input;
      currentPage.value = 1;
      search();
    };
    
    /**
     * Called on every facet selector change, updates the `facets.xxx` object then searches with new values 
     */
    const handleFacetChange = (facet) => {
      return (values) => {
        // Values can either be an array of varying length, or a String.
        if (Array.isArray(values)) {
          if (values.length > 1)
            facets.value[facet] = values.map((obj) => obj.value);
          else if (values.length === 1) facets.value[facet] = values[0].value;
          else facets.value[facet] = null;
        } else {
          if(values) {
            facets.value[facet] = values;
          } else {
            facets.value[facet] = null;
          }
        }
        currentPage.value = 1;
        search();
      };
    };

    /**
     * Called when user change sort
     */
    const handleSortChange = () => {
      currentPage.value = 1;
      search();
    }

    /**
     * Change current page
     * @param {number} page
     */
    const changePage = (page) => {
      currentPage.value = page;
      search();
      scrollToTop();
    };
    
    const scrollToTop = () => {
      if (searchRef.value) {
        searchRef.value.scrollIntoView({ behavior: "smooth" });
      }
    };

    const resetFilters = () => {
      facets.value = {};
      currentPage.value = 1;
      search();
    };

    const resetForm = () => {
      queryString.value = "";
      resetFilters();
    };

    /**
     * Is any filter active ?
     */ 
    const isFiltered = computed(() => {
      return Object.keys(facets.value).some(
        (key) => facets.value[key]?.length > 0
      );
    });

    const sortOptions = computed(() => props.sorts.map(sort => ({
        value: sort.order == 'asc' ? sort.value : '-' + sort.value,
        label: sort.label,
      })));

    const paramUrl = computed(() => {
      /**
       *  @type Record<string, string>
       */
      let params = {};
      for (key in facets.value) {
        if(facets.value[key]) {
          params[key] = facets.value[key];
        }
      }
      if (currentPage.value > 1) params.page = currentPage.value.toString();
      if (queryString.value) params.q = queryString.value;
      if(searchSort.value) params.sort = searchSort.value;
      return params;
    });

    const q = params.get('q');
    if (q) {
      queryString.value = q;
      params.delete('q');
    }
    const page = params.get('page');
    if (page) {
      currentPage.value = parseInt(page);
      params.delete('page');
    }
    const sort = params.get('sort');
    if(sort) {
      searchSort.value = sort;
      params.delete('sort');
    }
    /**
     * @type {Ref<{organization: ?string, tag: ?string, license: ?string, format: ?string, geozone: ?string, granularity: ?string, schema: ?string}>}
     */
    facets.value = Object.fromEntries(params);
    if (props.disableFirstSearch) {
      loading.value = true;
    } else {
      search();
    }

    watch(paramUrl, (val) => {
      // Update URL to match current search params value for deep linking
      let url = new URL(window.location.href);
      url.search = new URLSearchParams(val).toString();
      history.pushState(null, "", url);
      /** @type NodeListOf<HTMLAnchorElement> */
      let linksWithQuery = document.querySelectorAll('[data-q]');
      for (let link of linksWithQuery) {
        link.href = reuseUrl.value;
      }
    }, {deep: true});

    onMounted(() => {
      if (props.disableFirstSearch && resultsRef.value) {
        let total = resultsRef.value.dataset.totalResults;
        if (total && parseInt(total) > 0) {
          let datasetResults = resultsRef.value.dataset.results;
          if(datasetResults) {
            results.value = JSON.parse(datasetResults);
          }
          totalResults.value = JSON.parse(total);
        }
        loading.value = false;
      }
    });

    return {
      isFiltered,
      search,
      handleSearchChange,
      handleFacetChange,
      changePage,
      resetForm,
      resetFilters,
      facets,
      results,
      totalResults,
      queryString,
      loading,
      pageSize,
      currentPage,
      resultsRef,
      searchRef,
      sortOptions,
      searchSort,
      handleSortChange,
    };
  },
});
</script>
