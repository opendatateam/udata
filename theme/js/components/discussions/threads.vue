<template>
  <section class="discussions-wrapper">
    <div v-if="loading">
      <vue-content-loading
        class="mt-md"
        :width="950"
        :height="180"
        :speed="2"
        secondary="#7c7c7c"
        primary="#2d2d2d"
      >
        <rect x="0" y="0" rx="3" ry="3" width="490" height="10"></rect>
        <rect x="26" y="27" rx="5" ry="5" width="60" height="60"></rect>
        <rect x="97" y="29" rx="3" ry="3" width="120" height="8"></rect>
        <rect x="98" y="46" rx="3" ry="3" width="250" height="5"></rect>
        <rect x="98" y="59" rx="3" ry="3" width="250" height="5"></rect>
        <rect x="26" y="100" rx="5" ry="5" width="60" height="60"></rect>
        <rect x="97" y="100" rx="3" ry="3" width="120" height="8"></rect>
        <rect x="98" y="118" rx="3" ry="3" width="250" height="5"></rect>
        <rect x="98" y="131" rx="3" ry="3" width="250" height="5"></rect>
      </vue-content-loading>
    </div>
    <div v-else>
      Trié par : {{ current_sort.name }}
      <a @click.stop="changeSort(0)">Trier par créé</a>
      <a @click.stop="changeSort(1)">Trier par discussion</a>
      <ul>
        <li
          :id="'discussion-' + discussion.id"
          v-for="discussion in sortedDiscussions"
        >
          <thread v-bind="discussion" />
        </li>
      </ul>
      <create-thread
        :onSubmit="this.createThread"
        :subjectId="subjectId"
        :subjectClass="subjectClass"
      />
      <pagination
        v-if="total_results > page_size"
        :page="current_page"
        :page_size="page_size"
        :total_results="total_results"
        :changePage="changePage"
      />
    </div>
  </section>
</template>

<script>
import config from "../../config";
import VueContentLoading from "vue-content-loading";

import Pagination from "./pagination.vue";
import CreateThread from "./threads-create.vue";
import Thread from "./thread.vue";

const log = console.log;

const sorts = [
  { name: "Créé", getter: (item) => item.created, key: "-created" },
  {
    name: "Dernier post",
    getter: (item) =>
      item.discussion.length >= 1 && item.discussion.slice(-1)[0]["posted_on"],
    key: "-discussion[-1:].posted_on",
  },
];

export default {
  components: {
    "create-thread": CreateThread,
    Thread,
    Pagination,
    VueContentLoading,
  },
  data() {
    return {
      discussions: [],
      current_page: 1,
      page_size: 20,
      next_page: null,
      previous_page: null,
      total_results: 0,
      loading: true,
      current_sort: sorts[0],
    };
  },
  computed: {
    sortedDiscussions: function () {
      return this.discussions;
    },
  },
  props: {
    subjectId: String,
    subjectClass: String,
  },
  mounted() {
    this.loadPage(this.current_page);
  },
  methods: {
    loadPage: function (page = 1) {
      log("Loading page", page);
      this.loading = true;

      this.$api
        .get("/discussions/", {
          params: { page, for: this.subjectId, sort: this.current_sort.key },
        })
        .then((resp) => resp.data)
        .then((data) => {
          if (data.data) {
            this.discussions = data.data;
            this.total_results = data.total;
            this.next_page = data.next_page;
            this.previous_page = data.previous_page;
          }
        })
        .catch((err) => {
          log(err);
          this.$toasted.error("Error fetching discussions");
          this.discussion = [];
        })
        .finally(() => (this.loading = false));
    },
    changePage(index) {
      this.current_page = index;
      this.loadPage(index);
    },
    createThread: function (data) {
      const vm = this;
      return this.$api
        .post("/discussions/", data)
        .then(() => {
          vm.current_page = 1;
          vm.loadPage(1);
        })
        .catch((err) => this.$toasted.error("Error posting new thread", err));
    },
    changeSort: function (index = 0) {
      this.current_sort = sorts[index];
      this.loadPage(this.page);
    },
  },
};
</script>
