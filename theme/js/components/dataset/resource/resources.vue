<template>
  <section class="resources-wrapper" ref="top" key="top">
    <transition mode="out-in">
      <div v-if="loading" key="loader">
        <Loader class="mt-md" />
      </div>
      <div v-else>
        <Resource
          v-for="resource in resources"
          :id="'resource-' + resource.id"
          :dataset-id="datasetId"
          :resource="resource"
          :type-label="typeLabel"
          :can-edit="canEdit"
        />
        <Pagination
          class="fr-mt-3w"
          v-if="totalResults > pageSize"
          :page="currentPage"
          :page-size="pageSize"
          :total-results="totalResults"
          :change-page="changePage"
        />
      </div>
    </transition>
  </section>
</template>

<script>
import Loader from "../loader.vue";
import Pagination from "../../pagination/pagination.vue";
import Resource from "./resource.vue";
import config from "../../../config";

export default {
  name: "resources",
  components: {
    Loader,
    Pagination,
    Resource,
  },
  data() {
    return {
      resources: [],
      currentPage: 1,
      pageSize: config.resources_default_page_size,
      totalResults: 0,
      loading: true,
    };
  },
  props: {
    canEdit: {
      type: Boolean,
      required: true
    },
    datasetId: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      required: true,
    },
    typeLabel: {
      type: String,
      required: true,
    },
  },
  mounted() {
    this.loadPage(this.currentPage);
  },
  methods: {
    changePage(index, scroll = true) {
      this.currentPage = index;
      this.loadPage(index, scroll);
    },
    loadPage(page = 1, scroll = false) {
      this.loading = true;

      // We can pass the second function parameter "scroll" to true if we want to scroll to the top of the resources section
      // This is useful for pagination buttons
      if (this.$refs.top && scroll)
        this.$refs.top.scrollIntoView({ behavior: "smooth" });

      return this.$apiv2
        .get("/datasets/" + this.datasetId + "/resources/", {
          params: {
            page,
            type: this.type,
            page_size: this.pageSize,
          },
        })
        .then((resp) => resp.data)
        .then((data) => {
          if (data.data) {
            this.resources = data.data;
            this.totalResults = data.total;
          }
        })
        .catch(() => {
          this.$toast.error(
            this.$t("An error occurred while fetching resources")
          );
          this.resources = [];
        })
        .finally(() => {
          this.loading = false;
        });
    },
  }
}
</script>
