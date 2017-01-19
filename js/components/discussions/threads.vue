<template>
<div class="list-group resources-list smaller">
    <discussion-thread v-ref:threads v-for="discussion in discussions" :discussion="discussion" track-by="id">
    </discussion-thread>
    <a class="list-group-item add new-discussion" @click="displayForm" v-show="!formDisplayed">
        <div class="format-label pull-left">+</div>
        <h4 class="list-group-item-heading">{{ _('Start a new discussion') }}</h4>
    </a>
    <div class="list-group-item list-group-form list-group-form-discussion animated"
        v-show="formDisplayed" v-el:form>
        <div class="format-label pull-left">
            {{ current_user | display }}
        </div>
        <span class="list-group-item-link">
            <a href="#discussion-create"><span class="fa fa-link"></span></a>
        </span>
        <h4 class="list-group-item-heading">
            {{ _('Starting a new discussion thread') }}
        </h4>
        <p class="list-group-item-text">
            {{ _("You're about to start a new discussion thread. Make sure that a thread about the same topic doesn't exist yet just above.") }}
        </p>
        <threads-form v-ref:form :subject-id="subjectId" :subject-class="subjectClass"></threads-form>
    </div>
</div>
</template>

<script>
import DiscussionThread from 'components/discussions/thread.vue';
import ThreadsForm from 'components/discussions/threads-form.vue';
import log from 'logger';

export default {
    components: {DiscussionThread, ThreadsForm},
    data() {
        return {
            discussions: [],
            formDisplayed: false
        }
    },
    props: {
        subjectId: String,
        subjectClass: String
    },
    events: {
        /**
         * Add the created discussion in the list and display it
         * @type {Discussion} the newly created discussion
         */
        'discussion:created': function(discussion) {
            this.formDisplayed = false;
            this.discussions.unshift(discussion);
            this.$nextTick(() => {
                // Scroll to new discussion when displayed and expand it
                const $thread = this.$refs.threads.find($thread => $thread.discussion == discussion);
                $thread.detailed = true;
                this.$scrollTo($thread);
            });
        },
        /**
         * Replace the updated discussion in the list
         * @type {Discussion} the updated discussion
         */
        'discussion:updated': function(discussion) {
            const index = this.discussions.indexOf(this.discussions.find(d => d.id == discussion.id));
            // See: https://v1.vuejs.org/guide/list.html#Array-Change-Detection
            this.discussions.$set(index, discussion);
        }
    },
    ready() {
        this.$api.get('discussions', {for: this.subjectId}).then(response => {
            this.discussions = response.data;
        }).catch(log.error.bind(log));
    },
    methods: {
        displayForm() {
            this.formDisplayed = true;
        },

        /**
         * Trigger a new prefilled discussion.
         */
        start(title, comment) {
            this.formDisplayed = true;
            // Wait for next tick because the form needs to be visible to scroll
            this.$nextTick(() => {
                this.$scrollTo(this.$els.form);
                this.$refs.form.prefill(title, comment);
            })
        }
    }
}
</script>
