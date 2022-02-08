<!--
---
name: Suggest
category: Suggest
---

# Suggest-box

It's an input that searches with an autocomplete (typeahead) feature.
It searches using uData search API using separate API calls for Datasets and Reuses

## Architecture

The search is composed with multiple components :

* `<search-input>` is an input in which you can type in, the function you'll pass as a callback will be called on each change`
* `<suggest-box>` is the component that displays the suggest box (`search-input` + `suggest-results`). It's responsible for the API calls and such and is the "root" component of the suggest search and is mounted in the HTML.
* `<suggest-results>` is the component that displays the suggest results after you search for something.
* `<empty>` is the empty state component when no results have been found for a given suggest

## Progressive enhancement

We're doing progressive enhancement on this component.
This mean that users without Javascript will see a standard search input box that will redirect them to the `/search?q=query` endpoint.

In order to achieve this, the Jinja HTML template includes our Vue `<suggest>` element in the header, which is teleported to the `#app` component.
When the user starts to type, our Javascript will shift the whole page excepting the header to the left, and let the suggest box appear from the right.
For non-JS users, the home search box is a standard input that will still work normally, albeit without our fancy animations.

-->

<template>
  <transition name="suggest">
    <div
      v-if="active"
      @keyup.esc="stop()"
      class="suggest-wrapper bg-blue-300 fr-pb-4w"
      tabindex="0"
      ref="el"
    >
      <section>
        <div class="suggest-copy text-align-center my-xl">
          <h4>
            {{ $t("Search for data, reuses, contributions...") }}
          </h4>
        </div>
        <div class="fr-container">
          <div class="search-input-wrapper container-fluid">
            <search-input
              ref="searchInput"
              :value="queryString"
              :onChange="onChange"
              :stop="stop"
              :submitUrl="submitUrl"
            />
          </div>
          <div class="suggest-results">
            <transition name="enterOnly">
              <suggest-results
                :loading="loading"
                :results="results"
                :datasetUrl="datasetUrl"
                :reuseUrl="reuseUrl"
                :queryString="queryString"
                v-if="queryString"
              />
            </transition>
          </div>
        </div>
      </section>
    </div>
  </transition>
</template>

<script>
import config from "../../config";
import { generateCancelToken } from "../../plugins/api";

import SearchInput from "./search-input";
import SuggestResults from "./suggest-results";

const endpoints = [
  { name: "datasets", size: 4 },
  { name: "reuses", size: 2 },
];

export default {
  components: {
    SearchInput,
    SuggestResults,
  },
  data() {
    return {
      results: {},
      loading: true,
      currentRequest: null,
      queryString: "",
      active: false,
      submitUrl: config.values.datasetUrl,
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
  mounted() {
    this.$bus.on("suggest.startSearch", () => this.startSearch(""));
  },
  methods: {
    start() {
      this.active = true;
      const el = document.querySelector('#app');
      if (el) el.classList.add("suggesting");
    },
    stop() {
      this.active = false;
      const el = document.querySelector('#app');
      if (el) el.classList.remove("suggesting");
    },
    onChange(queryString) {
      // Deactivates the input if the user presses return while no query string is in
      if (this.queryString === "" && queryString === "") return this.stop();

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

      Promise.all(promises)
        .then((data) => {
          this.results = data.reduce((acc, val) => ({ ...acc, ...val }), {});
          this.loading = false;
        })
        .catch((err) => console.log(err));
    },
    async startSearch(string) {
      if (!string && this.active) return this.stop();

      this.start();

      if (string) {
        this.queryString = string;
        this.onChange(string);
      }
      window.scrollTo(0, 0);
    },
  },
};
</script>
