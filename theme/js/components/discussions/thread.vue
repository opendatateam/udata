<style scoped lang="less">
.panel .panel-heading {
    padding: 10px 15px;
    cursor: pointer;
}

.read-more {
    text-align: center;
    cursor: pointer;
}

.add-comment {

    padding: 10px 15px;

    & > button.btn {
        margin: 0 auto;
        display: block;
    }
}
</style>
<template>
<div class="discussion-thread panel panel-default">
    <div class="panel-heading" @click="toggleDiscussions">
        <div>
            <a href="#{{ discussionIdAttr }}" class="pull-right" v-on:click.stop><span class="fa fa-link"></span></a>
            <strong>{{ discussion.title }}</strong>
            <span class="label label-warning" v-if="discussion.closed"><i class="fa fa-minus-circle" aria-hidden="true"></i> {{ _('closed discussion') }}</span>
        </div>
    </div>
    <div class="list-group" v-show="detailed">
       <thread-message
           v-for="(index, response) in discussion.discussion"
           id="{{ discussionIdAttr }}-{{ index }}"
           :discussion="discussionIdAttr"
           :index="index"
           :message="response"
           class="list-group-item"
       ></threadmessage>
    </div>

    <div class="add-comment" v-show="detailed && !discussion.closed">
        <button v-show="!formDisplayed && detailed && !discussion.closed"
            type="button"
            class="btn btn-primary"
            @click="displayForm">
            {{ _('Add a comment') }}
        </button>
        <div v-el:form id="{{ discussionIdAttr }}-new-comment" v-show="formDisplayed && currentUser"
            class="animated form">
            <thread-form v-ref:form :discussion-id="discussion.id"></thread-form>
        </div>
    </div>

    <div class="panel-footer read-more" v-show="!detailed" @click="toggleDiscussions">
        <span class="text-muted">{{ discussion.discussion.length }} {{ _('messages') }}</span>
    </div>

    <div class="panel-footer" v-if="discussion.closed">
        <div class="text-muted">
            {{ _('Discussion has been closed') }}
            <span v-if="discussion.closed_by">
                {{ _('by') }} <a href="{{ discussion.closed_by.page }}">{{ discussion.closed_by | display }}</a>
            </span>
            {{ _('on') }} {{ closedDate }}
        </div>
    </div>
</div>
</template>

<script>
import config from 'config';
import ThreadMessage from 'components/discussions/message.vue';
import ThreadForm from 'components/discussions/thread-form.vue';
import moment from 'moment';
import Avatar from 'components/avatar.vue';

export default {
    components: {ThreadMessage, ThreadForm},
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
        }
    }
}
</script>
