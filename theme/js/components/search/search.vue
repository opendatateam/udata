<template>
  <div class="row-inline justify-between align-items-center search-bar">
    <search-input
      class="fr-my-1w fr-my-md-2w fr-text--lead fr-mb-0"
      :onChange="handleSearchChange"
      :value="queryString"
      :placeholder="$t('Search for data...')"
      ref="input"
    />
    <div
      class="filter-icon fr-hidden-md w-auto fr-mx-3v"
      :class="{ isFiltered, active: extendedForm }"
      v-html="filterIcon"
      @click="extendedForm = !extendedForm"
    ></div>
  </div>
  <div class="row-inline fr-mt-3v justify-between align-items-center">
    <h1 class="fr-m-0 fr-h4">
      {{ $t("Datasets") }}<sup>{{ totalResults || 0 }}</sup>
    </h1>
    <a :href="reuseUrl" title="" class="nav-link fr-text--sm fr-mb-0 fr-displayed-md fr-mt-3v">
      {{ $t("Search reuses") }}
    </a>
  </div>
  <section class="search-filters fr-p-2w fr-p-md-0" :class="{ active: extendedForm }">
    <h2 class="fr-mt-md-2w fr-mb-2w fr-mb-md-1w fr-text--sm">
      {{ $t("Search filters") }}
    </h2>
    <div class="filters-wrapper fr-p-md-3v">
      <div class="fr-grid-row fr-grid-row--gutters justify-between align-items-center">
        <div class="fr-col-12 fr-col-md-6 fr-col-lg-3">
          <Suggestor
            :placeholder="$t('Organizations')"
            :searchPlaceholder="$t('Search an organization...')"
            listUrl="/organizations/?sort=-followers"
            suggestUrl="/organizations/suggest/"
            entityUrl="/organizations/"
            :values="facets.organization"
            :onChange="handleSuggestorChange('organization')"
          />
        </div>
        <div class="fr-col-12 fr-col-md-6 fr-col-lg-3">
          <Suggestor
            :placeholder="$t('Tags')"
            :searchPlaceholder="$t('Search a tag...')"
            suggestUrl="/tags/suggest/"
            :values="facets.tag"
            :onChange="handleSuggestorChange('tag')"
          />
        </div>
        <div class="fr-col-12 fr-col-md-5 fr-col-lg-3">
          <Suggestor
            :placeholder="$t('Licenses')"
            :searchPlaceholder="$t('Search a license...')"
            listUrl="/datasets/licenses/"
            :values="facets.license"
            :onChange="handleSuggestorChange('license')"
          />
        </div>
        <div class="fr-col-12 fr-col-md-5 fr-col-lg-2">
          <Suggestor
            :placeholder="$t('Formats')"
            :searchPlaceholder="$t('Search a format...')"
            suggestUrl="/datasets/suggest/formats/"
            :values="facets.format"
            :onChange="handleSuggestorChange('format')"
          />
        </div>
        <div
          class="fr-col-2 fr-col-lg-1 fr-displayed-md text-align-center text-align-right-lg"
        >
          <button
            class="fr-btn fr-btn--secondary fr-btn--secondary-grey-200 text-grey-380 fr-px-2w"
            @click="extendedForm = !extendedForm"
            data-cy="extend-form"
          >
            <span v-if="!extendedForm">…</span>
            <span v-else>X</span>
          </button>
        </div>
      </div>
      <div
        v-if="extendedForm"
        data-cy="extended-form"
        class="fr-grid-row fr-grid-row--gutters fr-mt-3v align-items-center"
      >
        <div class="fr-col-12 fr-col-md-6 fr-col-lg-5 row-inline">
          <Rangepicker
            :value="facets.temporal_coverage"
            :onChange="handleSuggestorChange('temporal_coverage')"
          />
        </div>
        <div class="fr-col-12 fr-col-md-3">
          <Suggestor
            :placeholder="$t('Geographic area')"
            :searchPlaceholder="$t('Search a geographic area...')"
            suggestUrl="/spatial/zones/suggest/"
            entityUrl="/spatial/zone/"
            :values="facets.geozone"
            :onChange="handleSuggestorChange('geozone')"
          />
        </div>
        <div class="fr-col-12 fr-col-md-3">
          <Suggestor
            :placeholder="$t('Territorial granularity')"
            :searchPlaceholder="$t('Search a granularity...')"
            listUrl="/spatial/granularities/"
            :values="facets.granularity"
            :onChange="handleSuggestorChange('granularity')"
          />
        </div>
      </div>
    </div>
    <div class="fr-my-9v text-align-center fr-hidden-md">
      <button
        class="fr-btn fr-btn--secondary fr-btn--secondary-grey-400"
        @click="extendedForm = !extendedForm"
        >{{ $t("Submit") }}</button>
    </div>
  </section>
  <section class="bg-blue-100 fr-p-3v fr-mt-3w text-black">
    <span class="row-inline">
      <span class="fr-fi-question-line fr-mr-1w" aria-hidden="true"></span>
      <i18n-t keypath="Come try out our" tag="span">
        <template #dataset_search>
          <a :href="rechercherBetaPath">{{ $t('new dataset search') }}</a>
        </template>
      </i18n-t>
    </span>
  </section>
  <section class="search-results fr-mt-1w fr-mt-md-3w">
    <transition mode="out-in">
      <div v-if="loading">
        <Loader />
      </div>
      <ul v-else-if="results.length">
        <li
          v-for="result in results"
          :key="result.id"
        >
          <a
            :href="result.page"
            class="unstyled w-10 block"
          >
            <Dataset v-bind="result" />
          </a>
        </li>
        <Pagination
          v-if="totalResults > pageSize"
          :page="currentPage"
          :page-size="pageSize"
          :total-results="totalResults"
          :change-page="changePage"
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
          :onClick="() => resetFilters()"
        />
      </div>
    </transition>
  </section>
</template>

<script>
import config from "../../config";
import SearchInput from "./search-input";
import Suggestor from "./suggestor";
import Rangepicker from "./rangepicker";
import Dataset from "../dataset/search-result";
import Loader from "../dataset/loader";
import Empty from "./empty";
import Pagination from "../pagination/pagination";
import { generateCancelToken } from "../../plugins/api";
import filterIcon from "svg/filter.svg";
import axios from "axios";
import queryString from "query-string";

export default {
  components: {
    "search-input": SearchInput,
    Rangepicker,
    Suggestor,
    Dataset,
    Empty,
    Loader,
    Pagination,
  },
  created() {
    this.filterIcon = filterIcon;

    // Update search params from URL on page load for deep linking
    const url = new URL(window.location);
    let searchParams = queryString.parse(url.search);
    if (searchParams.q) {
      this.queryString = searchParams.q;
      delete searchParams.q;
    }
    if (searchParams.page) {
      this.currentPage = parseInt(searchParams.page);
      delete searchParams.page;
    }
    // set all other search params as facets
    this.facets = searchParams;
    this.search();
  },
  watch: {
    paramUrl: {
      deep: true,
      handler(val) {
        // Update URL to match current search params value for deep linking
        let url = new URL(window.location);
        const searchParams = queryString.stringify(val, { skipNull: true });
        url.search = searchParams;
        history.pushState(null, "", url);
      },
    },
  },
  data() {
    return {
      extendedForm: false, // On desktop, extended form is simply another row of filters. On mobile, form is hidden until extendedForm is triggered
      results: [],
      loading: false,
      currentRequest: null,
      pageSize: 20,
      currentPage: 1,
      totalResults: 0,
      queryString: "",
      facets: {},
      rechercherBetaPath: "https://rechercher.etalab.studio/",
    };
  },
  computed: {
    // Url for doing the same search (queryString only) on the reuse page
    reuseUrl() {
      return `${config.values.reuseUrl}?q=${this.queryString}`;
    },
    // Is any filter active ?
    isFiltered() {
      return Object.keys(this.facets).some(
        (key) => this.facets[key]?.length > 0
      );
    },
    paramUrl() {
      let params = {};
      for (key in this.facets) {
        params[key] = this.facets[key];
      }
      if (this.currentPage > 1) params.page = this.currentPage;
      if (this.queryString) params.q = this.queryString;
      return params;
    },
  },
  methods: {
    handleSearchChange(input) {
      this.queryString = input;
      this.currentPage = 1;
      this.search();
    },
    // Called on every facet selector change, updates the `facets.xxx` object then searches with new values
    handleSuggestorChange(facet) {
      return (values) => {
        // Values can either be an array of varying length, or a String.
        if (Array.isArray(values)) {
          if (values.length > 1)
            this.facets[facet] = values.map((obj) => obj.value);
          else if (values.length === 1) this.facets[facet] = values[0].value;
          else this.facets[facet] = null;
        } else {
          this.facets[facet] = values;
        }

        this.currentPage = 1;
        this.search();
      };
    },
    changePage(page) {
      this.currentPage = page;
      this.search();
      this.scrollToTop();
    },
    search() {
      this.loading = true;
      if (this.currentRequest) this.currentRequest.cancel();

      this.currentRequest = generateCancelToken();

      this.$api
        .get("/datasets/", {
          cancelToken: this.currentRequest.token,
          params: {
            q: this.queryString,
            ...this.facets,
            page_size: this.pageSize,
            page: this.currentPage,
          },
        })
        .then((res) => res.data)
        .then((result) => {
          this.results = result.data;
          this.totalResults = result.total;
          this.loading = false;
        })
        .catch((error) => {
          if (!axios.isCancel(error)) {
            this.$toast.error(this.$t("Error getting search results."));
            this.loading = false;
          }
        });
    },
    scrollToTop() {
      if (this.$refs.input)
        this.$refs.input.$el.scrollIntoView({ behavior: "smooth" });
    },
    resetFilters() {
      this.queryString = "";
      this.facets = {};
      this.currentPage = 1;
      this.search();
    },
  },
};
</script>
