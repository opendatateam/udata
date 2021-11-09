<template>
  <div class="thread-wrapper" :id="discussionUrl(id)">
    <header class="thread-header">
      <div class="thread-status" v-if="closed">
        <span>{{ $t("Discussion closed") }}</span>
      </div>
      <div class="thread-title">{{ title }}</div>
      <div class="thread-link">
        <a
          :aria-label="$t('Discussion permalink')"
          :href="discussionUrl(id, true)"
          v-html="LinkIcon"
        ></a>
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
          <div class="comment-meta">
            <avatar :user="comment.posted_by"></avatar>
            <div>
              <Author :author="comment.posted_by" :badge="false" />
              <div class="text-grey-300 mt-xxs">
                {{ $filters.formatDate(comment.posted_on) }}
              </div>
            </div>
            <div class="thread-link">
              <a
                :aria-label="$t('Comment permalink')"
                :href="commentUrl(id, index, true)"
                v-html="LinkIcon"
              ></a>
            </div>
          </div>
          <div class="thread-box">
            <p class="m-0">{{ comment.content }}</p>
          </div>
        </article>
      </transition-group>
      <article
        class="thread-collapse"
        v-if="_collapsed"
        @click.prevent="collapsed = false"
      >
        {{ _discussion.length }} {{ $t("messages") }}
      </article>
    </div>
    <footer class="thread-footer">
      <div v-if="!closed && !readOnlyEnabled">
        <a
          class="thread-reply-cta unstyled"
          v-if="!showForm"
          @click.stop="displayForm"
          tabindex="0"
        >
          {{ $t("Reply") }}
        </a>
        <thread-reply
          :subjectId="id"
          v-else="showForm"
          :onSubmit="replyToThread"
        />
      </div>
      <div v-if="closed" class="text-grey-300">
        {{ $t("The discussion was closed by") }} &#32;
        <span class="text-blue-200 px-xxs"><Author :author="closed_by" /></span>
        {{ $t("on") }} {{ $filters.formatDate(closed) }}
      </div>
    </footer>
  </div>
</template>

<script>
import ThreadReply from "./thread-reply.vue";
import Avatar from "./avatar.vue";
import Author from "./author.vue";
import LinkIcon from "svg/permalink.svg";
import config from "../../config";

export default {
  data() {
    return {
      showForm: false, //User has clicked on the "add comment" btn
      updatedDiscussion: null, //This is a bit ugly, we hold two states here for the updated discussion when the user replies. Should probably hoist this up.
      LinkIcon, //Little svg loading hack
      collapsed: true, //The thread is collapsed by default for closed discussions
      readOnlyEnabled: config.read_only_enabled,
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
    Author,
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
      this.$auth(
        this.$t("You must be logged in to start a discussion.")
      );
      this.showForm = true;
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
