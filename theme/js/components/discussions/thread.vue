<template>
  <div class="thread-wrapper" :id="discussionUrl(id)">
    <header class="thread-header">
      <div class="thread-status">Discussion fermée</div>
      <div class="thread-title">{{ title }}</div>
      <div class="thread-link"><a :href="discussionUrl(id, true)">Link</a></div>
    </header>
    <div class="thread-content">
      <article
        v-for="(comment, index) in _discussion"
        class="thread-comment"
        :id="commentUrl(id, index)"
      >
        <div class="avatar">
          <img src="https://placekitten.com/500/500" />
        </div>
        <div class="thread-box">
          <strong class="author">
            {{
              comment.posted_by.first_name + " " + comment.posted_by.last_name
            }}
          </strong>
          <p class="m-0">{{ comment.content }}</p>
        </div>
        <a :href="commentUrl(id, index, true)">Link</a>
      </article>
    </div>
    <footer class="thread-footer">
      <div class="thread-reply-cta" v-if="!showForm" @click.stop="showForm = true">+ Ajouter un commentaire</div>
      <thread-reply :subjectId="id" v-if="showForm" :onSubmit="replyToThread" />
    </footer>
  </div>
</template>

<script>
import ThreadReply from "./thread-reply.vue";

export default {
  data() {
    return {
      showForm: false,
      updatedDiscussion: null, //This is a bit ugly, we hold two states here for the updated discussion when the user replies. Should probably hoist this up.
    };
  },
  computed: {
    _discussion: function () {
      //And this is the logic to get either the original discussion passed in prop or the updated one
      return this.updatedDiscussion ? this.updatedDiscussion : this.discussion;
    },
  },
  components: {
    "thread-reply": ThreadReply,
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
  },
  props: {
    id: String,
    discussion: Array,
    title: String,
    url: String,
  },
};
</script>
