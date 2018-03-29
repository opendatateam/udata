<style lang="less">
</style>
<template>
<div class="discussion-thread panel panel-default">
    <div class="panel-heading">
        <div>
            <strong>{{ discussion.title }}</strong> <a href="#{{ discussionIdAttr }}"><span class="fa fa-link"></span></a> 
        </div>
    </div>
    <div class="list-group">
        <div v-for="(index, response) in discussion.discussion"
            id="{{ discussionIdAttr }}-{{ index }}"
            class="list-group-item list-group-indent animated discussion-messages-list"
            v-show="detailed">

            <div>{{{ response.content | markdown }}}</div>
            
            <div>
                <avatar :user="response.posted_by" :size="18"></avatar>
                {{ response.posted_by.first_name }} {{ response.posted_by.last_name }}
                {{ formatDate(response.posted_on) }} 
                <a href="#{{ discussionIdAttr }}-{{ index }}"><span class="fa fa-link"></span></a>
            </div>
        </div>
    </div>

    <div class="panel-footer">
    <a v-if="!discussion.closed"
        class="list-group-item add new-comment animated"
        v-show="!formDisplayed && detailed" @click="displayForm">
        <div class="format-label pull-left">+</div>
        <h4 class="list-group-item-heading">
            {{ _('Add a comment') }}
        </h4>
    </a>
    <div v-el:form id="{{ discussionIdAttr }}-new-comment" v-show="formDisplayed" v-if="currentUser"
        class="list-group-item animated">
        <thread-form v-ref:form :discussion-id="discussion.id"></thread-form>
    </div>
    </div>
</div>
</template>

<script>
import config from 'config';
import Avatar from 'components/avatar.vue';
import ThreadForm from 'components/discussions/thread-form.vue';
import moment from 'moment';

export default {
    components: {Avatar, ThreadForm},
    props: {
        discussion: Object,
        position: Number,
    },
    data() {
        return {
            detailed: true,
            formDisplayed: false,
            currentUser: config.user,
        }
    },
    events: {
        'discussion:updated': function(discussion) {
            // Hide the form on comment submitted
            this.hideForm()
            return true; // Don't stop propagation
        }
    },
    computed: {
        discussionIdAttr() {
            return `discussion-${this.discussion.id}`;
        },
        createdDate() {
            return moment(this.discussion.created).format('LL');
        },
        closedDate() {
            return moment(this.discussion.closed).format('LL');
        }
    },
    methods: {
        toggleDiscussions() {
            this.detailed = !this.detailed;
        },
        /**
         * Display the comment form or triggers an authentication if required
         */
        displayForm() {
            this.$auth(this._('You need to be logged in to comment.'));
            this.formDisplayed = true; // Form is at the end of the expanded discussion
            this.detailed = true;
        },
        /**
         * Hide the comment form
         */
        hideForm() {
            this.formDisplayed = false;
        },

        /**
         * Trigger a new prefilled comment.
         */
        start(comment) {
            this.displayForm()
            // Wait for next tick because the form needs to be visible to scroll
            this.$nextTick(() => {
                if (this.$els.form && this.$refs.form) { // Avoid logging errors
                    this.$scrollTo(this.$els.form);
                    this.$refs.form.prefill(comment);
                }
            })
        },

        /**
         * Focus the thread or a specific comment if position is given
         */
        focus(index) {
            this.detailed = true;
            if (index) {
                this.$nextTick(() => {
                    this.$scrollTo(`#${this.discussionIdAttr}-${index}`);
                })
            } else {
                this.$scrollTo(this);
            }
        },
        formatDate(val) {
            return moment(val).format('LL');
        }
    }
}
</script>
