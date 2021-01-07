<template>
  <div class="thread-wrapper" :id="discussionUrl(id)">
    <header class="thread-header">
      <div class="thread-status">
        <span v-if="closed">Discussion fermée</span>
      </div>
      <div class="thread-title">{{ title }}</div>
      <div class="thread-link">
        <a aria-label="Permalink to discussion" :href="discussionUrl(id, true)" v-html="LinkIcon"></a>
      </div>
    </header>
    <div class="thread-content">
      <transition-group name="list">
        <article
          v-for="(comment, index) in _discussion"
          v-if="!_collapsed"
          class="thread-comment"
          :id="commentUrl(id, index)"
          :key="commentUrl(id, index)"
        >
          <avatar :user="comment.posted_by"></avatar>
          <div class="thread-box">
            <strong class="author">
              {{
                comment.posted_by.first_name + " " + comment.posted_by.last_name
              }}
            </strong>
            <p class="m-0">{{ comment.content }}</p>
          </div>
          <div class="thread-link">
            <span class="thread-date">{{ formatDate(comment.posted_on) }}</span>
            <a aria-label="Permalink to comment" :href="commentUrl(id, index, true)" v-html="LinkIcon"></a>
          </div>
        </article>
      </transition-group>
      <article
        class="thread-collapse"
        v-if="_collapsed"
        @click.prevent="collapsed = false"
      >
        {{ _discussion.length }} messages
      </article>
    </div>
    <footer class="thread-footer">
      <div v-if="!closed">
        <div
          class="thread-reply-cta"
          v-if="!showForm"
          @click.stop="displayForm"
        >
          + Ajouter un commentaire
        </div>
        <thread-reply
          :subjectId="id"
          v-if="showForm"
          :onSubmit="replyToThread"
        />
      </div>
      <div v-if="closed" class="text-grey-300">
        La discussion a été close par&#32;
        <span class="text-blue-200 px-xxs">{{
          closed_by.first_name + " " + closed_by.last_name
        }}</span>
        le {{ formatDate(closed) }}
      </div>
    </footer>
  </div>
</template>

<script>
import ThreadReply from "./thread-reply.vue";
import Avatar from "./avatar.vue";
import LinkIcon from "svg/permalink.svg";
import dayjs from "dayjs";
import "dayjs/locale/fr";

dayjs.locale("fr");

export default {
  data() {
    return {
      showForm: false, //User has clicked on the "add comment" btn
      updatedDiscussion: null, //This is a bit ugly, we hold two states here for the updated discussion when the user replies. Should probably hoist this up.
      LinkIcon, //Little svg loading hack
      collapsed: true, //The thread is collapsed by default for closed discussions
    };
  },
  computed: {
    _discussion: function () {
      //And this is the logic to get either the original discussion passed in prop or the updated one
      return this.updatedDiscussion ? this.updatedDiscussion : this.discussion;
    },
    _collapsed() {
      return this.closed && this.collapsed;
    },
  },
  components: {
    "thread-reply": ThreadReply,
    Avatar,
  },
  methods: {
    discussionUrl: (id, link = false) => (link ? "#" : "") + "discussion-" + id, //Permalink helpers
    commentUrl: function (id, index, link = false) {
      return this.discussionUrl(id, link) + "-" + index;
    },
    replyToThread: function (values) {
      const vm = this;
      return this.$api
        .post("/discussions/" + vm.id + "/", values)
        .then((resp) => resp.data)
        .then((updatedDiscussion) => {
          this.updatedDiscussion = updatedDiscussion.discussion;
          this.showForm = false;
        });
    },
    displayForm: function () {
      this.$auth("You need to be logged in to start a discussion.");
      this.showForm = true;
    },
    formatDate: function (date) {
      return dayjs(date).format("D MMMM YYYY");
    },
  },
  props: {
    id: String,
    discussion: Array,
    title: String,
    url: String,
    closed: String,
    closed_by: Object,
  },
};
</script>
