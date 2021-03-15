<template>
  <search-input
    class="my-md fs-xl"
    :onChange="handleSearchChange"
    :value="queryString"
    :placeholder="$t('@@Recherchez des données...')"
    ref="input"
  />
  <div class="row-inline mt-sm justify-between align-items-center">
    <h1 class="m-0 h2">
      {{ $t("@@Jeux de données") }}<sup>{{ total_results || 0 }}</sup>
    </h1>
    <a :href="reuseUrl" title="" class="nav-link fs-sm">
      {{ $t("@@Rechercher dans les réutilisations") }}
    </a>
  </div>
  <section class="search-filters">
    <h4 class="mt-md mb-xs fs-sm">{{ $t("@@Critères de recherche") }}</h4>
    <div class="filters-wrapper p-sm">
      <div class="row justify-between align-items-center">
        <div class="col-3">
          <Suggestor
            :placeholder="$t('@@Organisations')"
            :searchPlaceholder="$t('@@Chercher une organisation...')"
            listUrl="/organizations/"
            suggestUrl="/organizations/suggest/"
            :values="facets.organization"
            :onChange="handleSuggestorChange('organization')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            :placeholder="$t('@@Mots clés')"
            :searchPlaceholder="$t('@@Chercher un mot clé...')"
            suggestUrl="/tags/suggest/"
            :values="facets.keywords"
            :onChange="handleSuggestorChange('keywords')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            :placeholder="$t('@@Licenses')"
            :searchPlaceholder="$t('@@Chercher une license...')"
            listUrl="/datasets/licenses/"
            :values="facets.license"
            :onChange="handleSuggestorChange('license')"
          />
        </div>
        <div class="col-2">
          <Suggestor
            :placeholder="$t('@@Formats')"
            :searchPlaceholder="$t('@@Chercher un format...')"
            suggestUrl="/datasets/suggest/formats/"
            :values="facets.format"
            :onChange="handleSuggestorChange('format')"
          />
        </div>
        <div class="col-1 text-align-center">
          <a class="btn-secondary btn-secondary-grey-200 px-md" @click="extendedForm = !extendedForm">
            <span v-if="!extendedForm">&#8230;</span>
            <span v-else>X</span>
          </a>
        </div>
      </div>
      <div v-if="extendedForm" class="row mt-sm align-items-center">
        <div class="col-5 row-inline">
          <Rangepicker
            :value="facets.temporal_coverage"
            :onChange="handleSuggestorChange('temporal_coverage')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            :placeholder="$t('@@Zone géographique')"
            :searchPlaceholder="$t('@@Chercher une zone...')"
            suggestUrl="/spatial/zones/suggest"
            :values="facets.geozone"
            :onChange="handleSuggestorChange('geozone')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            :placeholder="$t('@@Granularité géographique')"
            :searchPlaceholder="$t('@@Chercher une granularité...')"
            listUrl="/spatial/granularities"
            :values="facets.granularity"
            :onChange="handleSuggestorChange('granularity')"
          />
        </div>
      </div>
    </div>
  </section>
  <section class="search-results mt-lg">
    <transition mode="out-in">
      <div v-if="loading">
        <Loader />
      </div>
      <ul v-else-if="results.length">
        <a v-for="result in results" :href="result.page" class="unstyled w-100">
          <Dataset v-bind="result" />
        </a>
        <Pagination
          light
          v-if="total_results > page_size"
          :page="current_page"
          :page_size="page_size"
          :total_results="total_results"
          :changePage="changePage"
          class="mt-md"
        />
      </ul>
      <div v-else>
        <Empty
          wide
          :queryString="queryString"
          :cta="$t('@@Réinitialiser les filtres')"
          :copy="
            $t(
              '@@Nous n’avons pas de jeu de données correspondant à votre requête'
            )
          "
          :copyAfter="
            $t(
              '@@Vous pouvez essayer de réinitialiser les filtres pour agrandir votre champ de recherche.'
            )
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
    //Update facets from URL on page load for deep linking
    const url = new URL(window.location);
    const searchParams = queryString.parse(url.search);

    this.facets = searchParams;
    this.search();
  },
  watch: {
    facets: {
      deep: true,
      handler(val) {
        //Update URL to match current facets value for deep linking
        let url = new URL(window.location);
        const searchParams = queryString.stringify(val, { skipNull: true });
        url.search = searchParams;
        history.pushState(null, "", url);
      },
    },
  },
  data() {
    return {
      extendedForm: false,
      results: [],
      loading: false,
      currentRequest: null,
      page_size: 20,
      current_page: 1,
      total_results: 0,
      queryString: "",
      facets: {},
    };
  },
  computed: {
    //Url for doing the same search (queryString only) on the reuse page
    reuseUrl: function () {
      return (
        config.values.reuseUrl +
        (this.queryString ? "?q=" + this.queryString : "")
      );
    },
  },
  methods: {
    handleSearchChange(input) {
      this.queryString = input;
      this.search();
    },
    //Called on every facet selector change, updates the `facets.xxx` object then searches with new values
    handleSuggestorChange(facet) {
      const that = this;
      return function (values) {
        //Values can either be an array of varying length, or a String.
        if (Array.isArray(values)) {
          if (values.length > 1)
            that.facets[facet] = values.map((obj) => obj.value);
          else if (values.length === 1) that.facets[facet] = values[0].value;
          else that.facets[facet] = null;
        } else {
          that.facets[facet] = values;
        }

        that.search();
      };
    },
    changePage(page) {
      this.current_page = page;
      this.search();
      this.scrollToTop();
    },
    search() {
      this.loading = true;
      if (this.currentRequest) this.currentRequest.cancel();

      this.currentRequest = generateCancelToken();

      const promise = this.$api
        .get("/datasets/", {
          cancelToken: this.currentRequest.token,
          params: {
            q: this.queryString,
            ...this.facets,
            page_size: this.page_size,
            page: this.page,
          },
        })
        .then((res) => res.data)
        .then((result) => {
          this.results = result.data;
          this.total_results = result.total;
        })
        .finally(() => (this.loading = false));
    },
    scrollToTop() {
      if (this.$refs.input)
        this.$refs.input.$el.scrollIntoView({ behavior: "smooth" });
    },
    resetFilters() {
      this.queryString = "";
      this.facets = {};
      this.search();
    },
  },
};
</script>
