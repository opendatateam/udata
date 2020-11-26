<template>
  <section class="discussions-wrapper">
    <transition mode="out-in">
      <div v-if="loading" key="loader">
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
      <div v-if="!loading" ref="top" key="top">
        <div v-if="threadFromURL">
          You're seeing a single thread from your URL !
          <a @click.prevent="viewAllDiscussions">View all</a>
          <thread v-bind="threadFromURL"></thread>
        </div>
        <div v-else>
          Trié par : {{ current_sort.name }}
          <a @click.stop="changeSort(0)">Trier par créé</a>
          <a @click.stop="changeSort(1)">Trier par discussion</a>
          <ul>
            <li
              :id="'discussion-' + discussion.id"
              v-for="discussion in discussions"
            >
              <thread v-bind="discussion" />
            </li>
          </ul>
          <create-thread
            ref="createThread"
            :onSubmit="this.createThread"
            :subjectId="subjectId"
            :subjectClass="subjectClass"
          ></create-thread>
          <pagination
            v-if="total_results > page_size"
            :page="current_page"
            :page_size="page_size"
            :total_results="total_results"
            :changePage="changePage"
          />
        </div>
      </div>
    </transition>
  </section>
</template>

<script>
import config from "../../config";
import VueContentLoading from "vue-content-loading";

import Pagination from "../pagination/pagination.vue";
import CreateThread from "./threads-create.vue";
import Thread from "./thread.vue";

const log = console.log;
const URL_REGEX = /discussion-([a-f0-9]{24})-?([0-9]+)?$/i;

const sorts = [
  { name: "Créé", key: "-created" },
  {
    name: "Dernier post",
    key: "-discussion.posted_on",
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
      discussions: [], //Store list of discussions (page)
      threadFromURL: null, //Single thread (load from URL)
      current_page: 1, //Current pagination page
      page_size: 20,
      total_results: 0,
      loading: true,
      current_sort: sorts[0],
    };
  },
  props: {
    subjectId: String,
    subjectClass: String,
  },
  watch: {
    //Update DOM counter on results count change
    //Simply add .discussion-count class to any DOM element for it to be updated
    total_results: (count) => {
      const els = document.querySelectorAll(".discussions-count");
      if (els) els.forEach((el) => (el.innerHTML = count));
    },
  },
  mounted() {
    //Check if URL contains a thread
    const hash = window.location.hash.substring(1);
    const [a, discussionId, b] = URL_REGEX.exec(hash) || [];

    //If not, we load the first page
    if (!discussionId) return this.loadPage(this.current_page);

    //If it does, it gets loaded
    this.loadThread(discussionId);
  },
  methods: {
    //Loads a full page
    loadPage(page = 1, scroll = false) {
      log("Loading page", page);
      this.loading = true;

      //We can pass a second "scroll" variable to true if we want to scroll to the top of the dicussions section
      //This is useful for bottom of the page navigation buttons
      if (this.$refs.top && scroll)
        this.$refs.top.scrollIntoView({ behavior: "smooth" });

      return this.$api
        .get("/discussions/", {
          params: {
            page,
            for: this.subjectId,
            sort: this.current_sort.key,
            page_size: this.page_size,
          },
        })
        .then((resp) => resp.data)
        .then((data) => {
          if (data.data) {
            this.discussions = data.data;
            this.total_results = data.total;
          }
        })
        .catch((err) => {
          log(err);
          this.$toasted.error("Error fetching discussions");
          this.discussion = [];
        })
        .finally(() => {
          this.loading = false;
        });
    },
    //Loads a single thread, used to load a single thread from URL for instance
    loadThread(id) {
      if (!id) return;

      log("Loading thread", id);

      this.loading = true;

      return this.$api
        .get("/discussions/" + id)
        .then((resp) => resp.data)
        .then((data) => {
          if (data) {
            this.threadFromURL = data;
            this.total_results = 1;
          }
        })
        .catch((err) => {
          log(err);
          this.$toasted.error("Error fetching discussion " + id);
          this.loadPage(1); //In case loading a single comment didn't work, we load the first page. Better than nothing !
        })
        .finally(() => {
          this.loading = false;
        });
    },
    //Removes the specific discussion from URL
    //And loads the first page
    viewAllDiscussions() {
      this.threadFromURL = null;
      history.pushState(null, null, " ");
      this.loadPage(1);
    },
    //Pagination handler
    changePage(index, scroll = true) {
      this.current_page = index;
      this.loadPage(index, scroll);
    },
    //Can be called from outside the component to start a new thread programmatically
    startThread() {
      if (!this.$refs.createThread) return;

      this.$refs.createThread.displayForm();
      this.$refs.createThread.$el.scrollIntoView()
    },
    //Callback that will be passed to the create-thread component
    createThread(data) {
      const vm = this;
      return this.$api
        .post("/discussions/", data)
        .then(() => {
          vm.current_page = 1;
          vm.loadPage(1, true);
        })
        .catch((err) => this.$toasted.error("Error posting new thread", err));
    },
    //Changing sort order
    changeSort(index = 0) {
      this.current_sort = sorts[index];
      this.loadPage(this.page);
    },
  },
};
</script>
