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
          sending: false,
          comment: ''
      }
  },
  methods: {
      submit() {
          this.sending = true;
          this.$api
          .post(`discussions/${this.discussionId}/`, {comment: this.comment})
          .then(response => {
              this.$dispatch('discussion:updated', response);
              this.comment = '';
              this.sending = false;
          })
          .catch(err => {
              const msg = this._('An error occured while submitting your comment')
              Notify.error(msg)
              log.error(err)
              this.sending = false;
          });
      }
  }
}
</script>
