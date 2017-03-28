<template>
<div class="new-issue-form">
    <div class="modal-body">
        <p><strong>{{ _("You're about to submit a new issue related to a tendencious usage of the platform, illegal data opened or shameless advertisement. Note that questions and discussions about the data itself now takes place in the community section of each dataset.") }}</strong></p>
        <form role="form">
            <div class="form-group" >
                <label for="title">{{ _('Title') }}</label>
                <input type="text" id="title" v-model="title" class="form-control" required :disabled="sending"/>
            </div>
            <div class="form-group">
                <label for="comment">{{ _('Details') }}</label>
                <textarea id="comment" v-model="comment" class="form-control" rows="3" required :disabled="sending"></textarea>
            </div>
        </form>
    </div>
    <footer class="modal-footer text-center">
        <button class="btn btn-primary" @click="submit" :disabled="!canSubmit">
            <span class="fa fa-check"></span>
            {{ _('Submit') }}
        </button>
        <button class="btn btn-info" @click="$dispatch('back')" :disabled="sending">
            <span class="fa fa-step-backward"></span>
            {{ _('Back') }}
        </button>
        <button type="button" class="btn btn-default" @click="$dispatch('close')"  :disabled="sending">
            <span class="fa fa-times"></span>
            {{ _('Close') }}
        </button>
    </footer>
</div>
</template>

<script>
import log from 'logger';

export default {
    props: {
        subject: {type: Object, required: true},
    },
    data() {
        return {
            sending: false,
            title: '',
            comment: '',
        };
    },
    computed: {
        canSubmit() {
            return this.title && this.comment && !this.sending;
        }
    },
    methods: {
        submit() {
            if (this.canSubmit) {
                this.sending = true;
                this.$api
                    .post(`issues/`, {title: this.title, comment: this.comment, subject: this.subject})
                    .then(response => {
                        this.title = '';
                        this.comment = '';
                        this.sending = false;
                        this.$dispatch('issue:created', response);
                        this.$dispatch('notify:success', this._('Your issue has been sent to the team'));
                    })
                    .catch(err => {
                        this.$dispatch('notify:error', this._('An error occured while submitting your issue'));
                        log.error(err)
                        this.sending = false;
                    });
            }
        }
    }
};
</script>
<style lang="less"></style>
