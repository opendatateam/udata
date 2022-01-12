<!--
---
name: Results
category: Suggest
---

# Search results

Display datasets and reuses in a small box.
Used by the suggest feature to display typeahead-style results when you type your query.

-->

<template>
  <div class="row p-md results">
    <div class="p-md col col-md-12">
      <a
        class="unstyled row-inline justify-between see-all"
        :href="datasetUrl"
        :title="$t('Search all datasets')"
      >
        <h2>
          {{ $t("Datasets") }}
        </h2>
        <span v-html="arrow" />
      </a>
      <p class="text-grey-380 m-0">
        {{
          $t(
            "Datasets are collections of data, i.e. structured information, easily readable by a machine."
          )
        }}
      </p>
      <transition mode="out-in">
        <dataset-loader v-if="loading" />
        <Empty
          v-else-if="!results.datasets.length > 0"
          :cta="$t('See all datasets')"
          :copy="$t('No dataset matching your query')"
          :queryString="queryString"
          :link="datasetUrl"
        />
        <div class="my-md cards-container reuse-cards" v-else>
          <ul>
            <li v-for="dataset in results.datasets">
              <a :href="dataset.page" :title="dataset.title" class="unstyled">
                <Dataset v-bind="dataset" />
              </a>
            </li>
          </ul>
          <a class="nav-link pt-md" :href="datasetUrl">{{
            $t("Search in datasets")
          }}</a>
        </div>
      </transition>
    </div>
    <div class="p-md col col-md-12">
      <a
        class="unstyled row-inline justify-between see-all"
        :href="reuseUrl"
        :title="$t('Search in reuses')"
      >
        <h2>
          {{ $t("Reuses") }}
        </h2>
        <span v-html="arrow" />
      </a>
      <p class="text-grey-380 m-0">
        {{
          $t(
            "Reuses refer to the use of data for an other purpose than the one they were produced for."
          )
        }}
      </p>
      <transition mode="out-in">
        <reuse-loader class="my-md" v-if="loading" />
        <Empty
          v-else-if="!results.reuses.length > 0"
          :cta="$t('See the reuses')"
          :copy="$t('No reuse matching your query')"
          :queryString="queryString"
          :link="reuseUrl"
        />
        <div class="my-md cards-container" v-else>
          <ul class="row">
            <li v-for="reuse in results.reuses" class="col text-align-center">
              <a :href="reuse.page" :title="reuse.title" class="unstyled">
                <Reuse v-bind="reuse" />
              </a>
            </li>
          </ul>
          <a class="nav-link pt-md" :href="reuseUrl">{{
            $t("Search reuses")
          }}</a>
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
import Dataset from "../dataset/card";
import DatasetLoader from "../dataset/loader";
import Reuse from "../reuse/card";
import ReuseLoader from "../reuse/loader";
import Empty from "./empty.vue";
import Arrow from "svg/arrow-right.svg";

export default {
  created() {
    this.arrow = Arrow;
  },
  components: {
    Dataset,
    Reuse,
    DatasetLoader,
    ReuseLoader,
    Empty,
  },
  props: {
    datasetUrl: String,
    reuseUrl: String,
    results: Object,
    loading: Boolean,
    queryString: String,
  },
};
</script>
