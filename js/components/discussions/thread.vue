<template>
<div>
    <div class="list-group-item" id="{{ discussionIdAttr }}" @click="toggleDiscussions">
        <div class="format-label pull-left">
            <avatar :user="question.posted_by"></avatar>
        </div>
        <span class="list-group-item-link">
            <a href="#{{ discussionIdAttr }}"><span class="fa fa-link"></span></a>
        </span>
        <h4 class="list-group-item-heading ellipsis open-discussion-thread">
            <span>{{ discussion.title }}</span>
        </h4>
        <p class="list-group-item-text ellipsis open-discussion-thread list-group-message-number-{{ discussion.id }}">
            {{ _('Discussion started on') }} {{ discussion.created | dt }} {{ _('with') }}
            {{ _('nbmessages', {nb: responses.length}) }}
        </p>
    </div>
    <div v-for="(index, response) in responses" id="{{ discussionIdAttr }}-{{ index }}"
        class="list-group-item list-group-indent animated discussion-messages-list"
        :class="{'body-only': index == 0, 'hidden': !detailed}">
        <template v-if="index > 0">
            <div class="format-label pull-left">
                {{ response.posted_by | display }}
            </div>
            <span class="list-group-item-link">
                <a href="#{{ discussionIdAttr }}-{{ index }}"><span class="fa fa-link"></span></a>
            </span>
        </template>
        <p class="list-group-item-heading">
            {{ response.content | markdown }}
        </p>
    </div>
    <a v-if="!discussion.closed"
        class="list-group-item add new-comment list-group-indent animated"
        :class="{hidden: formDisplayed || !detailed}"
        @click="displayForm">
        <div class="format-label pull-left">+</div>
        <h4 class="list-group-item-heading">
            {{ _('Add a comment') }}
        </h4>
    </a>
    <div class="list-group-item list-group-form list-group-indent animated"
        id="{{ discussionIdAttr }}-{{ position }}"
        :class="{hidden: !formDisplayed}">
        <div class="format-label pull-left">
            {{ current_user | display }}
        </div>
        <span class="list-group-item-link">
            <a href="#{{ discussionIdAttr }}-{{ position }}"><span class="fa fa-link"></span></a>
        </span>
        <h4 class="list-group-item-heading">
            {{ _('Commenting on this thread') }}
        </h4>
        <p class="list-group-item-text">
            {{ _("You're about to answer to this particular thread about:") }}<br />
            {{ discussion.title }}
        </p>
        <thread-form :discussion-id="discussion.id"></thread-form>
    </div>
</div>
</template>

<script>
import Avatar from 'components/avatar.vue';
import ThreadForm from 'components/discussions/thread-form.vue';

export default {
    props: {
        discussion: Object,
        position: Number,
    },
    data() {
        return {
            detailed: false,
            formDisplayed: false,
        }
    },
    computed: {
        question() {
            return this.discussion.discussion[0];
        },
        responses() {
            return this.discussion.discussion.splice(1);
        },
        discussionIdAttr() {
            return `discussion-${this.discussion.id}`;
        }
    },
    ready() {
        this.$on('discussion-load', discussion => {
            this.discussion = discussion;
        });
    },
    methods: {
        toggleDiscussions() {
            this.detailed = !this.detailed;
        },
        displayForm() {
            this.formDisplayed = true;
        }
    },
    components: {Avatar, ThreadForm}
}
</script>
