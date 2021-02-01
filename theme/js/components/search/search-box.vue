<template>
  <section class="search-wrapper bg-blue-300">
    <div class="container">
      <search-input :onChange="onChange" />
      <div class="row p-md results">
        <div class="p-md col col-md-12">
          <h2>
            Jeux de données <sup>{{ results?.datasets?.length || 0 }}</sup>
          </h2>
          <p class="text-grey-300 m-0">
            Nullam neque bibendum convallis enim aliquam. Integer egestas
            accumsan, in varius lectus. Elementum a facilisis nibh pellentesque
            enim egestas porta.
          </p>
          <dataset-loader v-if="loading" />
          <Empty
            v-else-if="!results.datasets.length > 0"
            :cta="$t('@@Voir tous les jeux de données')"
            :copy="
              $t(
                '@@Nous n’avons pas de jeu de données correspondant à votre requête'
              )
            "
            :queryString="queryString"
            :link="datasetUrl"
          />
          <div class="my-md cards-container" v-else>
            <ul>
              <li v-for="dataset in results.datasets">
                <a :href="dataset.page" :title="dataset.title" class="unstyled">
                  <Dataset v-bind="dataset" />
                </a>
              </li>
            </ul>
            <a class="nav-link pt-md" :href="datasetUrl">{{
              $t("@@Rechercher dans les jeux de données")
            }}</a>
          </div>
        </div>
        <div class="p-md col col-md-12">
          <h2>
            Réutilisations <sup>{{ results?.reuses?.length || 0 }}</sup>
          </h2>
          <p class="text-grey-300 m-0">
            Nullam neque bibendum convallis enim aliquam. Integer egestas
            accumsan, in varius lectus. Elementum a facilisis nibh pellentesque
            enim egestas porta.
          </p>
          <reuse-loader class="my-md" v-if="loading" />
          <Empty
            v-else-if="!results.reuses.length > 0"
            :cta="$t('@@Voir toutes les réutilisations')"
            :copy="
              $t(
                '@@Nous n’avons pas de réutilisation correspondant à votre requête'
              )
            "
            :queryString="queryString"
            :link="reuseUrl"
          />
          <div class="my-md cards-container" v-else>
            <ul class="reuse-cards row">
              <li v-for="reuse in results.reuses" class="col text-align-center">
                <a :href="reuse.page" :title="reuse.title" class="unstyled">
                  <Reuse v-bind="reuse" />
                </a>
              </li>
            </ul>
            <a class="nav-link pt-md" :href="reuseUrl">{{
              $t("@@Rechercher dans les réutilisations")
            }}</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import SearchInput from "./search-input";
import Dataset from "../dataset/card";
import DatasetLoader from "../dataset/loader";
import Reuse from "../reuse/card";
import ReuseLoader from "../reuse/loader";
import Empty from "./empty.vue";

import config from "../../config";
import { generateCancelToken } from "../../plugins/api";

const endpoints = [
  { name: "datasets", size: 4 },
  { name: "reuses", size: 2 },
];

export default {
  components: {
    SearchInput,
    Dataset,
    Reuse,
    DatasetLoader,
    ReuseLoader,
    Empty,
  },
  data() {
    return {
      results: {},
      loading: true,
      currentRequest: null,
      queryString: "",
    };
  },
  computed: {
    datasetUrl() {
      return `${config.values.datasetUrl}?q=${this.queryString}`;
    },
    reuseUrl() {
      return `${config.values.reuseUrl}?q=${this.queryString}`;
    },
  },
  methods: {
    onChange(queryString) {
      this.loading = true;
      this.queryString = queryString;

      if (this.currentRequest) this.currentRequest.cancel();

      this.currentRequest = generateCancelToken();

      const promises = endpoints.map(({ name, size }) =>
        this.$api
          .get(name + "/suggest/", {
            cancelToken: this.currentRequest.token,
            params: {
              q: queryString,
              size,
            },
          })
          .then((res) => ({
            [name]: res.data,
          }))
      );

      Promise.all(promises).then((data) => {
        this.results = data.reduce((acc, val) => ({ ...acc, ...val }), {});
        this.loading = false;
      });
    },
  },
};
</script>
