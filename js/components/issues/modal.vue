<style lang="less">
.issue-modal {
    h3 {
        margin-top: 0;
    }

    .direct-chat-messages {
        height: auto;
    }
}
</style>

<template>
<w-modal title="{{ _('Issue') }}"
    modalclass="issue-modal"
    v-ref="modal">
    <div class="modal-body">
        <h3>{{ issue.title }}</h3>
        <div class="direct-chat-messages">
            <div class="direct-chat-msg"
                v-repeat="message:issue.discussion">
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
        <form v-if="!issue.closed">
            <div class="form-group">
                <textarea class="form-control" rows="3"
                    placeholder="{{ _('Type your comment') }}"
                    v-model="comment"
                    required>
                </textarea>
            </div>
        </form>
        <button type="button" class="btn btn-success btn-flat pointer pull-left"
            v-on="click: comment_issue" v-if="!issue.closed">
            {{ _('Comment the issue') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat pointer pull-left"
            v-on="click: close_issue" v-if="!issue.closed">
            {{ _('Comment and close issue') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Close') }}
        </button>
    </footer>
</w-modal>
</template>

<script>
'use strict';

var API = require('api'),
    Vue = require('vue');

module.exports = {
    name: 'issue-modal',
    mixins: [require('components/form/base-form')],
    replace: false,
    components: {
        'w-modal': require('components/modal.vue'),
    },
    data: function() {
        return {
            issueid: null,
            issue: {},
            avatar_placeholder: require('helpers/placeholders').user,
            comment: null
        };
    },
    props: ['issueid'],
    ready: function() {
        API.issues.get_issue({id: this.issueid}, function(response) {
            this.issue = response.obj;
            this.$emit('issue:loaded');
        }.bind(this));
    },
    methods: {
        close_issue: function() {
            this.send_comment(this.comment, true);
        },
        comment_issue: function() {
            this.send_comment(this.comment);
        },
        send_comment: function(comment, close) {
            if (this.validate()) {
                API.issues.comment_issue({id: this.issueid, payload: {
                    comment: comment,
                    close: close || false
                }}, function(response) {
                    this.issue = response.obj;
                    this.$emit('issue:loaded');
                }.bind(this));
            }
        }
    }
};
</script>
