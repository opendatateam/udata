<template>
<form role="form" class="clearfix animated" @submit.prevent="submit">
    <div class="form-group">
        <label for="comment-new-message">{{ _('Comment') }}</label>
        <textarea id="comment-new-message" v-model="comment" class="form-control" rows="3" required></textarea>
    </div>
    <button @click="submit" :disabled="this.sending || !this.comment" class="btn btn-primary btn-block pull-right submit-new-message">
        {{ _('Submit your comment') }}
    </button>
</form>
</template>

<script>
import i18n from 'i18n';
import Auth from 'auth';
import log from 'logger';
import Notify from 'notify';

export default {
  props: {
      discussionId: String
  },
  data() {
      return {
          // Flags to `true` when the form is in sending process. This prevents
          // duplicate POSTing.
          sending: false
      }
  },
  methods: {
      submit() {
          if (!Auth.need_user(i18n._('You need to be logged in to comment.'))) {
              return;
          }
          this.sending = true;
          this.$api
          .post(`discussions/${this.discussionId}/`, {comment: this.comment})
          .then(response => {
              this.$dispatch('discussion-load', response);
              this.comment = '';
              this.sending = false;
          })
          .catch(err => {
              const msg = i18n._('An error occured while submitting your comment')
              Notify.error(msg)
              log.error(err)
              this.sending = false;
          });
      }
  }
}
</script>
