<template>
<form role="form" class="clearfix animated" @submit.prevent="submit">
    <div class="form-group">
        <label for="title-new-discussion">{{ _('Title') }}</label>
        <input type="text" id="title-new-discussion" v-model="title" class="form-control" required />
        <label for="comment-new-discussion">{{ _('Comment') }}</label>
        <textarea v-el:textarea id="comment-new-discussion" v-model="comment" class="form-control" rows="3" required></textarea>
    </div>
    <button type="submit" :disabled="this.sending || !this.title || !this.comment" class="btn btn-primary btn-block pull-right submit-new-discussion">
        {{ _('Start a discussion') }}
    </button>
</form>
</template>

<script>
import Auth from 'auth';
import log from 'logger';
import Notify from 'notify';

export default {
    props: {
        subjectId: String,
        subjectClass: String,
        position: Number
    },
    data() {
        return {
            sending: false,
            title: '',
            comment: ''
        }
    },
    methods: {
        /**
         * Prefill the form and focus the comment area
         */
        prefill(title, comment) {
            comment = comment || '';
            this.comment = comment;
            this.title = title || '';
            this.$els.textarea.setSelectionRange(comment.length, comment.length);
            this.$els.textarea.focus();
        },
        submit() {
            const data = {
                title: this.title,
                comment: this.comment,
                subject: {
                    id: this.subjectId,
                    class: this.subjectClass,
                }
            };
            this.sending = true;
            this.$api
            .post('discussions/', data)
            .then(response => {
                this.$dispatch('discussion:created', response);
                this.title = '';
                this.comment = '';
                this.sending = false;
                document.location.href = `#discussion-${response.id}`;
            })
            .catch(err => {
                const msg = this._('An error occured while submitting your comment');
                Notify.error(msg);
                log.error(err);
                this.sending = false;
            });
        }
    }
}
</script>
