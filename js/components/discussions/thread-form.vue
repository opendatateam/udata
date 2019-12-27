<template>
<form role="form" class="clearfix animated" @submit.prevent="submit">
    <div class="form-group">
        <label :for="id">{{ _('Comment') }}</label>
        <textarea v-el:textarea :id="id" v-model="comment" class="form-control" rows="3" required></textarea>
    </div>
    <button type="submit" :disabled="this.sending || !this.comment" class="btn btn-primary btn-block pull-right submit-new-message">
        {{ _('Submit your comment') }}
    </button>
</form>
</template>

<script>
import log from 'logger';

export default {
  props: {
      discussionId: String
  },
  data() {
      return {
          // Flags to `true` when the form is in sending process. This prevents
          // duplicate POSTing.
          sending: false,
          comment: '',
          id: `new-comment-${this.discussionId}`
      }
  },
    methods: {
      /**
       * Prefill the form and focus the comment area
       */
      prefill(comment) {
          comment = comment || '';
          this.comment = comment;
          this.$els.textarea.setSelectionRange(comment.length, comment.length);
          this.$els.textarea.focus();
      },
      submit() {
          this.sending = true;
          this.$api
          .post(`discussions/${this.discussionId}/`, {comment: this.comment})
          .then(response => {
              this.$dispatch('discussion:updated', response);
              this.comment = '';
              this.sending = false;
              document.location.href = `#discussion-${this.discussionId}-${response.discussion.length - 1}`;
          })
          .catch(err => {
              const msg = this._('An error occured while submitting your comment');
              this.$dispatch('notify.error', msg);
              log.error(err);
              this.sending = false;
          });
      }
  }
}
</script>
