<template>
  <search-input
    class="my-md fs-xl"
    :onChange="handleSearchChange"
    :value="queryString"
    placeholder="Recherchez des données..."
    ref="input"
  />
  <div class="row-inline mt-sm justify-between align-items-center">
    <h1 class="m-0 h2">
      Jeux de données<sup>{{ total_results || 0 }}</sup>
    </h1>
    <a href="" title="" class="nav-link fs-sm">
      Rechercher dans les réutilisations
    </a>
    <!-- TODO : link this-->
  </div>
  <section class="search-filters">
    <h4 class="mt-md mb-xs fs-sm">Critères de recherche</h4>
    <div class="filters-wrapper p-xs">
      <div class="row justify-between align-items-center">
        <div class="col-3">
          <Suggestor
            placeholder="Organisations"
            searchPlaceholder="Chercher une organisation..."
            listUrl="/organizations/"
            suggestUrl="/organizations/suggest/"
            :onChange="handleSuggestorChange('organization')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            placeholder="Mots clés"
            suggestUrl="/tags/suggest/"
            :onChange="handleSuggestorChange('keywords')"
          />
        </div>
        <div class="col-3">
          <Suggestor
            placeholder="Licenses"
            listUrl="/datasets/licenses/"
            :onChange="handleSuggestorChange('license')"
          />
        </div>
        <div class="col-2">
          <Suggestor
            placeholder="Formats"
            suggestUrl="/datasets/suggest/formats/"
            :onChange="handleSuggestorChange('format')"
          />
        </div>
        <div class="col-1">
          <a class="btn btn-grey-100" @click="extendedForm = !extendedForm">
            <span v-if="!extendedForm">&#8230;</span>
            <span v-else>X</span>
          </a>
        </div>
      </div>
      <div
        v-if="extendedForm"
        class="row-inline justify-between align-items-center"
      >
        <select>
          <option>Plage temporelle</option>
        </select>
        <select>
          <option>Zone géographique</option>
        </select>
        <select>
          <option>Granularité géographique</option>
        </select>
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
import Dataset from "../dataset/search-result";
import Loader from "../dataset/loader";
import Empty from "./empty";
import Pagination from "../pagination/pagination";
import { generateCancelToken } from "../../plugins/api";

export default {
  components: {
    "search-input": SearchInput,
    Suggestor,
    Dataset,
    Empty,
    Loader,
    Pagination,
  },
  created() {
    //TODO : queryString from URL
    this.search();
  },
  watch: {
    facets: function(val) {
      console.log(val)
    }
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
  methods: {
    handleSearchChange(input) {
      this.queryString = input;
      this.search();
    },
    handleSuggestorChange(facet) {
      const that = this;
      return function (values) {
        that.facets[facet] = values.map((obj) => obj.value);
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
    },
  },
};
</script>
