<template>
<div class="issue-details">
    <div class="modal-body">
        <div class="media" v-for="comment in issue.discussion">
            <a class="pull-left" :href="comment.posted_by.page">
                <avatar :user="comment.posted_by"></avatar>
            </a>
            <div class="media-body">
                <div class="message text-left">
                    <p>{{{ comment.content|markdown }}}</p>
                </div>
            </div>
        </div>
        <form role="form" :action="issue.url">
             <div class="form-group">
                <label for="comment">{{ _('Comment') }}</label>
                <textarea id="comment" v-model="comment" class="form-control" rows="3" required></textarea>
            </div>
        </form>
    </div>
    <footer class="modal-footer text-center">
        <button class="btn btn-primary" @click="submitComment" :disabled="!canSubmit">
            <span class="fa fa-comment"></span>
            {{ _('Comment') }}
        </button>
        <button class="btn btn-primary" @click="submitCommentAndClose" :disabled="!canSubmit">
            <span class="fa fa-comments-o"></span>
            {{ _('Comment and close') }}
        </button>
        <button class="btn btn-info" @click="$dispatch('back')" :disabled="sending">
            <span class="fa fa-step-backward"></span>
            {{ _('Back') }}
        </button-->
        <button type="button" class="btn btn-default" @click="$dispatch('close')" :disabled="sending">
            <span class="fa fa-times"></span>
            {{ _('Close') }}
        </button>
    </footer>
</div>
</template>
<script>
import log from 'logger';
import Avatar from 'components/avatar.vue';

export default {
    components: {Avatar},
    props: {
        issue: {type: Object, required: true},
    },
    data() {
        return {
            comment: '',
        };
    },
    computed: {
        canSubmit() {
            return this.comment && !this.sending;
        }
    },
    methods: {
        submitComment() {
            this.submit(
                false,
                this._('Your comment has been sent to the team'),
                this._('An error occured while submitting your comment')
            );
        },
        submitCommentAndClose() {
            this.submit(
                true,
                this._('The issue has been closed'),
                this._('An error occured while closing the issue')
            );
        },
        submit(close, success, error) {
            this.$auth(this._('You need to be logged in to submit a comment.'));
            if (!this.canSubmit) return;
            this.$api
                .post(`issues/${this.issue.id}/`, {close, comment: this.comment})
                .then(response => {
                    this.comment = '';
                    this.sending = false;
                    this.$dispatch('issue:updated', response);
                    this.$dispatch('notify:success', success);
                })
                .catch(err => {
                    this.$dispatch('notify:error', error);
                    log.error(err)
                    this.sending = false;
                });
        }
    }
};
</script>
<style lang="less"></style>
