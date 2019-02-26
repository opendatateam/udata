<style lang="less">
.issue-modal {
    h3 {
        margin-top: 0;
    }

    .direct-chat-messages {
        height: auto;
    }

    .direct-chat-timestamp {
        color: #eee;
    }

    .direct-chat-text {
        background: #fff;
        border: 1px solid #fff;

        &:before, &:after {
            border-right-color: #fff;
        }
    }

    .card-container {
        margin-bottom: 1em;
    }
}
</style>

<template>
<modal v-ref:modal :title="_('Issue')" class="modal-info issue-modal" large>
    <div class="modal-body">
        <div class="row card-container">
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
                    :src="message.posted_by | avatar_url 40"/>
                <div class="direct-chat-text" v-markdown="message.content"></div>
            </div>
        </div>
    </div>
    <footer class="modal-footer text-center">
        <form v-if="can_comment" v-el:form>
            <div class="form-group">
                <textarea class="form-control" rows="3" :class="{'has-success': formValid}"
                    :placeholder="_('Type your comment')"
                    v-model="comment" required>
                </textarea>
            </div>
        </form>
        <button type="button" class="btn btn-info btn-flat pull-left"
            @click="$refs.modal.close">
            {{ _('Close') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat" :disabled="!formValid"
            @click="comment_issue" v-if="can_comment">
            {{ _('Comment the issue') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat" :disabled="!formValid"
            @click="close_issue" v-if="can_close">
            {{ _('Comment and close issue') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import Vue from 'vue';
import Modal from 'components/modal.vue';
import DatasetCard from 'components/dataset/card.vue';
import ReuseCard from 'components/reuse/card.vue';

export default {
    name: 'issue-modal',
    components: {Modal, DatasetCard, ReuseCard},
    data() {
        return {
            issue: {},
            comment: null,
            next_route: null
        };
    },
    computed: {
        can_comment() {
            return !this.issue.closed;
        },
        can_close() {
            return this.issue.subject && !this.issue.closed && this.$root.me.can_edit(this.issue.subject);
        },
        formValid() {
            return this.comment && this.comment.length > 0;
        }
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
                const idx = this.$route.matched.length - 2;
                const parent = this.$route.matched[idx];
                this.next_route = {
                    name: parent.handler.name,
                    params: parent.params
                };
            }
            const id = this.$route.params.issue_id;
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
            if (this.formValid) {
                API.issues.comment_issue({id: this.issue.id, payload: {
                    comment: comment,
                    close: close || false
                }}, (response) => {
                    this.issue = response.obj;
                    this.comment = null;
                }, this.$root.handleApiError);
            }
        }
    }
};
</script>
