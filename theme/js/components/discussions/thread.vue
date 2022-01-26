<template>
  <div class="bg-contrast-grey fr-mt-2w" :id="discussionUrl(id)">
    <header class="fr-grid-row fr-grid-row--middle justify-between fr-py-2w fr-px-3w">
      <div class="fr-col-auto text-default-warning fr-text--bold fr-pr-2w" v-if="closed">
        <span>{{ $t("Discussion closed") }}</span>
      </div>
      <h3 class="fr-p-2w fr-p-md-0 fr-h6 fr-mb-0">{{ title }}</h3>
      <div class="text-align-right">
        <a
          :id="id + '-copy'"
          :href="discussionUrl(id, true)"
          :data-clipboard-text="discussionExternalUrl(id)"
          class="fr-link fr-link--icon-right fr-fi-links-fill unstyled"
        >
          {{$t('Copy permalink')}}
        </a>
      </div>
    </header>
    <div>
      <transition-group name="list">
        <article
          v-for="comment in _discussion"
          v-if="!_collapsed"
          class="thread-comment fr-py-3w fr-px-3w fr-pr-5w"
          :key="'comment-' + comment.id"
        >
          <div class="fr-grid-row fr-grid-row--gutters">
            <avatar class="fr-col-auto" :user="comment.posted_by"></avatar>
            <div class="fr-col">
              <Author :author="comment.posted_by" :badge="false" />
              <div class="fr-text--sm text-mention-grey fr-mb-0">
                {{ $filters.formatDate(comment.posted_on) }}
              </div>
              <div class="white-space-pre-wrap">
                <p class="fr-mt-3v fr-mb-0">{{ comment.content }}</p>
              </div>
            </div>
          </div>
        </article>
      </transition-group>
      <div class="fr-grid-row" v-if="_collapsed">
        <button
        class="fr-px-3w fr-col fr-link text-mention-grey fr-text--sm fr-mb-0 rounded-0"
        @click.prevent="collapsed = false"
      >
        {{ _discussion.length }} {{ $t("messages") }}
      </button>
      </div>
    </div>
    <footer class="fr-py-2w fr-px-3w">
      <template v-if="!closed && !readOnlyEnabled">
        <button
          class="btn--flex btn-secondary btn-secondary-grey-500 fr-btn fr-btn--secondary fr-btn--icon-right fr-fi-arrow-right-s-line"
          v-if="!showForm"
          @click.stop="displayForm"
        >
          {{ $t("Reply") }}
        </button>
        <thread-reply
          :subjectId="id"
          v-else
          :onSubmit="replyToThread"
          @close="showForm = false"
        />
      </template>
      <div v-if="closed" class="text-grey-380">
        {{ $t("The discussion was closed by") }} &#32;
        <strong class="px-xxs"><Author :author="closed_by" /></strong>
        {{ $t("on") }} {{ $filters.formatDate(closed) }}
      </div>
    </footer>
  </div>
</template>

<script>
import ThreadReply from "./thread-reply.vue";
import Avatar from "./avatar.vue";
import Author from "./author.vue";
import config from "../../config";

export default {
  components: {
    "thread-reply": ThreadReply,
    Avatar,
    Author,
  },
  props: {
    id: String,
    discussion: Array,
    title: String,
    url: String,
    closed: String,
    closed_by: Object,
  },
  data() {
    return {
      showForm: false,
      updatedDiscussion: null,
      collapsed: true,
      readOnlyEnabled: config.read_only_enabled,
    };
  },
  computed: {
    _discussion() {
      // Discussion updates are saved locally only
      // This is the logic to get either the original discussion or the updated one
      return this.updatedDiscussion ? this.updatedDiscussion : this.discussion;
    },
    _collapsed() {
      return this.closed && this.collapsed;
    },
  },
  methods: {
    discussionUrl(id, link = false) {
      return (link ? "#" : "") + "discussion-" + id;
    },
    discussionExternalUrl(id) {
      hash = this.discussionUrl(id, true)
      return window.location.origin + window.location.pathname + hash
    },
    replyToThread (values) {
      return this.$api
        .post("/discussions/" + this.id + "/", values)
        .then((resp) => resp.data)
        .then((updatedDiscussion) => {
          this.updatedDiscussion = updatedDiscussion.discussion;
          this.showForm = false;
        });
    },
    displayForm() {
      this.$auth();
      this.showForm = true;
    },
  }
};
</script>
