<style lang="less">
.discussion-modal {
    h3 {
        margin-top: 0;
    }

    .direct-chat-messages {
        height: auto;
    }
}
</style>

<template>
<modal title="{{ _('Discussion') }}"
    class="discussion-modal"
    v-ref="modal">
    <div class="modal-body">
        <dataset-card v-if="discussion.class | is_dataset"
            datasetid="{{discussion.subject}}"></dataset-card>
        <reuse-card v-if="discussion.class | is_reuse"
            reuseid="{{discussion.subject}}"></reuse-card>
        <h3>{{ discussion.title }}</h3>
        <div class="direct-chat-messages">
            <div class="direct-chat-msg"
                v-repeat="message:discussion.discussion">
                <div class="direct-chat-info clearfix">
                    <span class="direct-chat-name pull-left">{{message.posted_by | display}}</span>
                    <span class="direct-chat-timestamp pull-right">{{message.posted_on | dt}}</span>
                </div>
                <img class="direct-chat-img"  alt="{{ _('User Image') }}"
                    v-attr="src:message.posted_by.avatar || avatar_placeholder"/>
                <div class="direct-chat-text" v-markdown="{{message.content}}"></div>
            </div>
        </div>
    </div>
    <footer class="modal-footer text-center">
        <form v-if="!discussion.closed">
            <div class="form-group">
                <textarea class="form-control" rows="3"
                    placeholder="{{ _('Type your comment') }}"
                    v-model="comment"
                    required>
                </textarea>
            </div>
        </form>
        <button type="button" class="btn btn-danger btn-flat pointer pull-left"
            v-if="$root.me.is_admin" v-on="click: confirm_delete">
            {{ _('Delete') }}
        </button>
        <button type="button" class="btn btn-success btn-flat pointer pull-left"
            v-on="click: comment_discussion" v-if="!discussion.closed">
            {{ _('Comment the discussion') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat pointer pull-left"
            v-on="click: close_discussion" v-if="!discussion.closed">
            {{ _('Comment and close discussion') }}
        </button>
        <button type="button" class="btn btn-primary btn-flat pointer"
            data-dismiss="modal">
            {{ _('Close') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API  from 'api';
import Vue from 'vue';

export default {
    name: 'discussion-modal',
    mixins: [require('components/form/base-form')],
    replace: false,
    components: {
        'modal': require('components/modal.vue'),
        'dataset-card': require('components/dataset/card.vue'),
        'reuse-card': require('components/reuse/card.vue'),
    },
    data: function() {
        return {
            discussionid: null,
            discussion: {},
            avatar_placeholder: require('helpers/placeholders').user,
            comment: null
        };
    },
    filters: {
        is_dataset: function(kind) {
            if (!kind) return;
            return kind.startsWith('Dataset');
        },
        is_reuse: function(kind) {
            if (!kind) return;
            return kind.startsWith('Reuse');
        }
    },
    props: ['discussionid'],
    ready: function() {
        API.discussions.get_discussion({id: this.discussionid}, function(response) {
            this.discussion = response.obj;
            this.$emit('discussion:loaded');
        }.bind(this));
    },
    methods: {
        confirm_delete: function() {
            this.$.modal.close();
            var m = this.$root.$modal(
                {data: {discussionid: this.discussion.id}},
                Vue.extend(require('components/discussions/delete-modal.vue'))
            );
        },
        close_discussion: function() {
            this.send_comment(this.comment, true);
        },
        comment_discussion: function() {
            this.send_comment(this.comment);
        },
        send_comment: function(comment, close) {
            if (this.validate()) {
                API.discussions.comment_discussion({id: this.discussionid, payload: {
                    comment: comment,
                    close: close || false
                }}, function(response) {
                    this.discussion = response.obj;
                    this.$emit('discussion:loaded');
                }.bind(this));
            }
        }
    }
};
</script>
