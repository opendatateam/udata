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
<modal v-ref:modal :title="_('Issue')" class="issue-modal" size="lg">
    <div class="modal-body">
        <div class="row">
            <dataset-card class="col-xs-12 col-md-offset-3 col-md-6"
                v-if="issue.subject | is 'dataset'"
                :datasetid="issue.subject.id"></dataset-card>
            <reuse-card class="col-xs-12 col-md-offset-3 col-md-6"
                v-if="issue.subject | is 'reuse'"
                :reuseid="issue.subject.id"></reuse-card>
        </div>
        <h3>{{ issue.title }}</h3>
        <div class="direct-chat-messages">
            <div class="direct-chat-msg"
                v-for="message in issue.discussion">
                <div class="direct-chat-info clearfix">
                    <span class="direct-chat-name pull-left">{{message.posted_by | display}}</span>
                    <span class="direct-chat-timestamp pull-right">{{message.posted_on | dt}}</span>
                </div>
                <img class="direct-chat-img"  :alt="_('User Image')"
                    :src="message.posted_by.avatar || avatar_placeholder"/>
                <div class="direct-chat-text" v-markdown="message.content"></div>
            </div>
        </div>
    </div>
    <footer class="modal-footer text-center">
        <form v-if="!issue.closed" v-el:form>
            <div class="form-group">
                <textarea class="form-control" rows="3"
                    :placeholder="_('Type your comment')"
                    v-model="comment" required>
                </textarea>
            </div>
        </form>
        <button type="button" class="btn btn-success btn-flat pointer pull-left"
            @click="comment_issue" v-if="!issue.closed">
            {{ _('Comment the issue') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat pointer pull-left"
            @click="close_issue" v-if="!issue.closed">
            {{ _('Comment and close issue') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Close') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import Vue from 'vue';
import BaseForm from 'components/form/base-form';

export default {
    name: 'issue-modal',
    mixins: [BaseForm],
    components: {
        'modal': require('components/modal.vue'),
        'dataset-card': require('components/dataset/card.vue'),
        'reuse-card': require('components/reuse/card.vue'),
    },
    data: function() {
        return {
            issue: {},
            avatar_placeholder: require('helpers/placeholders').user,
            comment: null,
            next_route: null
        };
    },
    events: {
        'modal:closed': function() {
            this.$go(this.next_route);
        }
    },
    route: {
        data() {
            if (this.$route.matched.length > 1) {
                // This is a nested view
                let idx = this.$route.matched.length - 2,
                    parent = this.$route.matched[idx];
                this.next_route = {
                    name: parent.handler.name,
                    params: parent.params
                };
            }
            let id = this.$route.params.issue_id;
            API.issues.get_issue({id}, (response) => {
                this.issue = response.obj;
            });
        }
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
                API.issues.comment_issue({id: this.issue.id, payload: {
                    comment: comment,
                    close: close || false
                }}, (response) => {
                    this.issue = response.obj;
                    this.comment = null;
                });
            }
        }
    }
};
</script>
