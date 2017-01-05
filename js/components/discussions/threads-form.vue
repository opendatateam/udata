<template>
<form role="form" class="clearfix animated" @submit.prevent="submit">
    <div class="form-group">
        <label for="title-new-discussion">{{ _('Title') }}</label>
        <input type="text" id="title-new-discussion" v-model="title" class="form-control" required />
        <label for="comment-new-discussion">{{ _('Comment') }}</label>
        <textarea id="comment-new-discussion" v-model="comment" class="form-control" rows="3" required></textarea>
    </div>
    <button type="submit" :disabled="this.sending || !this.title || !this.comment" class="btn btn-primary btn-block pull-right submit-new-discussion">
        {{ _('Start a discussion') }}
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
        submit() {
            if (!Auth.need_user(i18n._('You need to be logged in to comment.'))) {
                return;
            }
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
                this.$dispatch('discussions-load', response);
                this.title = '';
                this.comment = '';
                this.sending = false;
                document.location.href = `#discussion-${response.id}`
            })
            .catch(err => {
                const msg = i18n._('An error occured while submitting your comment');
                Notify.error(msg);
                log.error(err);
                this.sending = false;
            });
        }
    }
}
</script>
