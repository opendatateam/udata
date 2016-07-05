<template>
<div class="list-group resources-list smaller">
    <discussion-thread v-for="discussion in discussions" :discussion="discussion">
    </discussion-thread>
    <a class="list-group-item add new-discussion"
        @click="displayForm"
        :class="{hidden: formDisplayed}">
        <div class="format-label pull-left">+</div>
        <h4 class="list-group-item-heading">
            {{ _('Start a new discussion') }}
        </h4>
    </a>
    <div class="list-group-item list-group-form list-group-form-discussion animated"
        :class="{hidden: !formDisplayed}">
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
        <threads-form :subject-id="subjectId" :subject-class="subjectClass"></threads-form>
    </div>
</div>
</template>

<script>
import DiscussionThread from 'components/discussions/thread.vue';
import ThreadsForm from 'components/discussions/threads-form.vue';
import log from 'logger';

export default {
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
    ready() {
        this.$api.get('discussions', {for: this.subjectId}).then(response => {
            this.discussions = response.data;
        }).catch(log.error.bind(log));

        this.$on('discussions-load', discussions => {
            this.discussions = discussions;
        });
    },
    methods: {
        displayForm() {
            this.formDisplayed = true;
        }
    },
    components: {DiscussionThread, ThreadsForm}
}
</script>
