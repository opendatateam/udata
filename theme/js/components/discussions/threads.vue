<template>
  <section class="discussions-wrapper">
    <ModalsContainer></ModalsContainer>
    <transition mode="out-in">
      <div v-if="loading" key="loader">
        <Loader class="mt-md" />
      </div>
      <div v-else ref="top" key="top">
        <div v-if="threadFromURL">
          <div class="well well-secondary-green-300">
            <div class="row-inline justify-between">
              {{
                $t("You are seeing a specific discussion about this dataset")
              }}
              <a
                @click.prevent="viewAllDiscussions"
                class="unstyled"
                v-html="CloseIcon"
              ></a>
            </div>
          </div>
          <thread v-bind="threadFromURL"></thread>
          <a
            class="nav-link text-white mt-xl"
            @click.prevent="viewAllDiscussions"
            >{{ $t("See all discussions about this dataset") }}</a
          >
        </div>
        <div v-else>
          <div class="row-inline justify-end align-items-center">
            {{ $t("Sort by:") }}
            <div class="dropdown btn-secondary-white ml-md">
              <select
                name="sortBy"
                id="sortBy"
                @change="changeSort(current_sort)"
                v-model="current_sort"
                class="ml-xs"
              >
                <option
                  v-for="sort in sorts"
                  :value="sort"
                  :selected="sort === current_sort"
                >
                  {{ sort.name }}
                </option>
              </select>
            </div>
          </div>
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
            :onSubmit="createThread"
            :subjectId="subjectId"
            :subjectClass="subjectClass"
            v-show="!readOnlyEnabled"
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
import i18n from "../../plugins/i18n";

import Pagination from "../pagination/pagination.vue";
import CreateThread from "./threads-create.vue";
import Thread from "./thread.vue";
import Loader from "./loader.vue";
import CloseIcon from "svg/close.svg";

const log = console.log;
const URL_REGEX = /discussion-([a-f0-9]{24})-?([0-9]+)?$/i;

const sorts = [
  { name: i18n.global.t("Discussion creation"), key: "-created" },
  {
    name: i18n.global.t("Last reply"),
    key: "-discussion.posted_on",
  },
];

export default {
  components: {
    "create-thread": CreateThread,
    Thread,
    Pagination,
    Loader,
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
      sorts,
      CloseIcon,
      readOnlyEnabled: config.read_only_enabled,
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
          this.$toast.error(
            this.$t("An error occurred while fetching discussions")
          );
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
          this.$toast.error(
            this.$t("An error occurred while fetching the discussion ") + id
          );
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
      this.$refs.createThread.$el.scrollIntoView();
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
        .catch((err) =>
          this.$toast.error(
            this.$t("An error occurred while creating the discussion "),
            err
          )
        );
    },
    //Changing sort order
    changeSort(sort) {
      this.current_sort = sort;
      this.loadPage(this.page);
    },
  },
};
</script>
