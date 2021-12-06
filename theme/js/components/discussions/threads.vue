<!--
---
name: Discussions
category: Interactions
---

# Discussions

Discussions allow users to interact with others.

-->

<template>
  <section class="discussions-wrapper" ref="top" key="top">
    <div class="fr-grid-row">
      <div class="fr-col">
        <h2 id="community-discussions" class="fr-h2">{{ title }} <sup>{{totalResults}}</sup></h2>
        <slot></slot>
      </div>
      <div class="fr-col-12 fr-col-sm-6 fr-col-md-5 fr-col-lg-4 fr-grid-row fr-grid-row--bottom flex-direction-column justify-between" v-if="!threadFromURL">
        <ThreadsCreateButton class="fr-col--bottom" :onClick="startThreadWithoutScroll"/>
        <div class="fr-mt-5v">
          <select
          name="sortBy"
          id="sortBy"
          @change="changeSort(currentSort)"
          v-model="currentSort"
          class="fr-select bg-beige fr-select--no-border"
        >
          <option
            v-for="sort in sorts"
            :value="sort"
            :selected="sort === currentSort"
          >
            {{ sort.name }}
          </option>
        </select>
        </div>
      </div>
    </div>
    <transition mode="out-in">
      <template v-if="loading" key="loader">
        <Loader class="mt-md" />
      </template>
      <template v-else>
        <div v-if="threadFromURL">
          <div class="fr-mt-2w fr-px-3w well well-secondary-green-300">
            <div class="fr-grid-row fr-grid-row--middle justify-between">
              {{
                $t("You are seeing a specific discussion about this dataset")
              }}
              <button class="fr-link--close fr-link fr-mr-0" @click.prevent="viewAllDiscussions">
                {{$t('Close')}}
              </button>
            </div>
          </div>
          <thread v-bind="threadFromURL"></thread>
          <button
            class="nav-link nav-link--no-icon text-decoration-none fr-link fr-mt-9v fr-link--icon-left fr-fi-arrow-right-s-line"
            @click.prevent="viewAllDiscussions"
          >
            <span class="text-decoration-underline">{{ $t("See all discussions about this dataset") }}</span>
          </button>
        </div>
        <div v-else>
          <create-thread
            ref="createThread"
            :onSubmit="createThread"
            :subjectId="subjectId"
            :subjectClass="subjectClass"
            v-if="!readOnlyEnabled"
          ></create-thread>
          <ul class="fr-mb-5v">
            <li
              :id="'discussion-' + discussion.id"
              v-for="discussion in discussions"
            >
              <thread v-bind="discussion" />
            </li>
          </ul>
          <pagination
            v-if="totalResults > pageSize"
            :page="currentPage"
            :page-size="pageSize"
            :total-results="totalResults"
            :changePage="changePage"
          />
        </div>
      </template>
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
import ThreadsCreateButton from "./threads-create-button";

const URL_REGEX = /discussion-([a-f0-9]{24})-?([0-9]+)?$/i;

const sorts = [
  { name: i18n.global.t("Discussion creation"), key: "-created" },
  {
    name: i18n.global.t("Last reply"),
    key: "-discussion.posted_on",
  },
];

const defaultTitle = i18n.global.t("Discussions");

export default {
  components: {
    ThreadsCreateButton,
    "create-thread": CreateThread,
    Thread,
    Pagination,
    Loader,
  },
  data() {
    return {
      discussions: [], // Store list of discussions (page)
      threadFromURL: null, // Single thread (load from URL)
      currentPage: 1, // Current pagination page
      pageSize: 5,
      totalResults: 0,
      loading: true,
      currentSort: sorts[0],
      sorts,
      CloseIcon,
      readOnlyEnabled: config.read_only_enabled,
    };
  },
  props: {
    description: String,
    subjectId: String,
    subjectClass: String,
    title: {
      type: String,
      default: defaultTitle,
    }
  },
  watch: {
    // Update DOM counter on results count change
    // Simply add .discussion-count class to any DOM element for it to be updated
    totalResults: (count) => {
      const els = document.querySelectorAll(".discussions-count");
      if (els) els.forEach((el) => (el.innerHTML = count));
    },
  },
  mounted() {
    // Listen to bus events
    this.$bus.on("discussions.startThread", () => this.startThread());

    // Check if URL contains a thread
    const hash = window.location.hash.substring(1);
    const [a, discussionId, b] = URL_REGEX.exec(hash) || [];

    // If not, we load the first page
    if (!discussionId) return this.loadPage(this.currentPage);

    // If it does, it gets loaded
    this.loadThread(discussionId);
  },
  methods: {
    // Loads a full page
    loadPage(page = 1, scroll = false) {
      this.loading = true;

      // We can pass a second "scroll" variable to true if we want to scroll to the top of the discussions section
      // This is useful for bottom of the page navigation buttons
      if (this.$refs.top && scroll) {
        this.$refs.top.scrollIntoView({ behavior: "smooth" });
      }

      return this.$api
        .get("/discussions/", {
          params: {
            page,
            for: this.subjectId,
            sort: this.currentSort.key,
            page_size: this.pageSize,
          },
        })
        .then((resp) => resp.data)
        .then((data) => {
          if (data.data) {
            this.discussions = data.data;
            this.totalResults = data.total;
          }
        })
        .catch((err) => {
          this.$toast.error(
            this.$t("An error occurred while fetching discussions")
          );
          this.discussion = [];
        })
        .finally(() => {
          this.loading = false;
        });
    },
    // Loads a single thread, used to load a single thread from URL for instance
    loadThread(id) {
      if (!id) return;
      this.loading = true;

      // Scroll the discussion block into view.
      // SetTimeout is needed (instead of $nextTick) because the DOM updates are too fast for the browser to handle
      setTimeout(
        () => this.$refs.top.scrollIntoView({ behavior: "smooth" }),
        500
      );

      return this.$api
        .get("/discussions/" + id)
        .then((resp) => resp.data)
        .then((data) => {
          if (data) {
            this.threadFromURL = data;
            this.totalResults = 1;
          }
        })
        .catch((err) => {
          this.$toast.error(
            this.$t("An error occurred while fetching the discussion ") + id
          );
          this.loadPage(1); // In case loading a single comment didn't work, we load the first page. Better than nothing !
        })
        .finally(() => {
          this.loading = false;
        });
    },
    // Removes the specific discussion from URL
    // And loads the first page
    viewAllDiscussions() {
      this.threadFromURL = null;
      history.pushState(null, null, " ");
      this.loadPage(1);
    },
    // Pagination handler
    changePage(index, scroll = true) {
      this.currentPage = index;
      this.loadPage(index, scroll);
    },
    // Can be called from outside the component to start a new thread programmatically and scroll into view
    startThread() {
      this.startThreadWithoutScroll();
      this.$refs.createThread.$el.scrollIntoView();
    },
    // Can be called from outside the component to start a new thread programmatically
    startThreadWithoutScroll() {
      if (!this.$refs.createThread) return;
      this.$refs.createThread.displayForm();
    },
    // Callback that will be passed to the create-thread component
    createThread(data) {
      return this.$api
        .post("/discussions/", data)
        .then(() => {
          this.currentPage = 1;
          this.loadPage(1, true);
        })
        .catch((err) =>
          this.$toast.error(
            this.$t("An error occurred while creating the discussion "),
            err
          )
        );
    },
    // Changing sort order
    changeSort(sort) {
      this.currentSort = sort;
      this.loadPage(this.page);
    },
  },
};
</script>
