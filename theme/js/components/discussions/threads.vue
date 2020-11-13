<template>
  <section class="discussions-wrapper">
    <h1 v-if="loading">Im a LOADER</h1>
    <div>
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
    </div>
  </section>
</template>

<script>
import config from "../../config";
import CreateThread from "./threads-create.vue";
import Thread from "./thread.vue";

const log = console.log;
const sorts = [
  { name: "Créé", getter: (item) => item.created },
  {
    name: "Dernier post",
    getter: (item) =>
      item.discussion.length >= 1 && item.discussion.slice(-1)[0]["posted_on"],
  },
];

export default {
  components: {
    "create-thread": CreateThread,
    "thread": Thread
  },
  data() {
    return {
      discussions: [],
      current_page: 1,
      loading: true,
      current_sort: sorts[0],
    };
  },
  computed: {
    sortedDiscussions: function () {
      return this.discussions.sort(
        (a, b) =>
          new Date(this.current_sort.getter(b)) -
          new Date(this.current_sort.getter(a))
      );
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
        .get("/discussions/", { params: { page: page } })
        .then((resp) => resp.data)
        .then((data) => {
          if (data.data) this.discussions = data.data;
        })
        .catch((err) => {
          log(err);
          this.discussion = [];
        })
        .finally(() => (this.loading = false));
    },
    createThread: function (data) {
      const vm = this;
      return this.$api.post("/discussions/", data).then(() =>{
        vm.current_page = 1;
        vm.loadPage(1);
      });
    },
    changeSort: function (index = 0) {
      this.current_sort = sorts[index];
    },
  },
};
</script>
