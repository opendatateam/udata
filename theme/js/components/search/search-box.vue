<template>
  <section class="search-wrapper bg-blue-300">
    <div class="container col-12">
      <search-input :onChange="onChange" />
      <div class="row">
        <div class="col col-md-12">
          <h2>
            Jeux de données <sup>{{ results?.datasets?.length || 0 }}</sup>
          </h2>
          <p class="text-grey-300">
            Nullam neque bibendum convallis enim aliquam. Integer egestas
            accumsan, in varius lectus. Elementum a facilisis nibh pellentesque
            enim egestas porta.
          </p>

          <ul>
            <li v-for="dataset in results.datasets">
              <a :href="dataset.page" :title="dataset.title" class="unstyled">
                <Dataset v-bind="dataset" />
              </a>
            </li>
          </ul>
          <a class="nav-link mt-md" :href="datasetUrl"
            >Rechercher dans les jeux de données</a
          >
        </div>
        <div class="col col-md-12">
          <h2>
            Réutilisations <sup>{{ results?.reuses?.length || 0 }}</sup>
          </h2>
          <p class="text-grey-300">
            Nullam neque bibendum convallis enim aliquam. Integer egestas
            accumsan, in varius lectus. Elementum a facilisis nibh pellentesque
            enim egestas porta.
          </p>

          <ul class="reuse-cards">
            <li v-for="reuse in results.reuses">
              <a :href="reuse.page" :title="reuse.title" class="unstyled">
                <Reuse v-bind="reuse" />
              </a>
            </li>
          </ul>
          <a class="nav-link mt-md" :href="reuseUrl"
            >Rechercher dans les réutilisations</a
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import SearchInput from "./search-input";
import Dataset from "../dataset/card";
import Reuse from "../reuse/card";

import config from "../../config";
import { generateCancelToken } from "../../plugins/api";

const endpoints = ["datasets", "reuses"];

export default {
  components: {
    SearchInput,
    Dataset,
    Reuse,
  },
  data() {
    return {
      results: {},
      loading: false,
      currentRequest: null,
      queryString: "",
    };
  },
  computed: {
    datasetUrl() {
      return `${config.values.datasetUrl}?q=${this.queryString}`
    },
    reuseUrl() {
      return `${config.values.reuseUrl}?q=${this.queryString}`
    }
  },
  methods: {
    onChange(queryString) {
      this.loading = true;
      this.queryString = queryString;

      if (this.currentRequest) this.currentRequest.cancel();

      this.currentRequest = generateCancelToken();

      const promises = endpoints.map((endpoint) =>
        this.$api
          .get(endpoint + "/suggest/", {
            cancelToken: this.currentRequest.token,
            params: {
              q: queryString,
              size: 4,
            },
          })
          .then((res) => ({
            [endpoint]: res.data,
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
