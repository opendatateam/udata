<!--
    Issue modal for a given object.
-->
<template>
<modal class="object-issues-modal" v-ref:modal :title="title">
    <component :is="view" v-ref:view :subject="subject" :issue="issue"></component>
</modal>
</template>

<script>
import moment from 'moment';
import Modal from 'components/modal.vue';
import pubsub from 'pubsub';

import Display from './object-modal-display.vue';
import New from './object-modal-new.vue';
import List from './object-modal-list.vue';

export default {
    components: {Modal, List, New, Display},
    props: {
        subject: {type: Object, required: true},
    },
    data() {
        return {
            view: 'list',
            issue: null
        };
    },
    computed: {
        title() {
            if (this.view === 'display') {
                return `${this.issue.title} <small>(${this.issueDate})</small>`;
            } else if (this.view === 'new') {
                return this._('New issue');
            } else {
                return this._('Issues');
            }
        },
        issueDate() {
            if (this.issue) return moment(this.issue.created).format('LLL');
        }
    },
    events: {
        new() {
            this.$auth(this._('You need to be logged in to submit a new issue.'));
            this.view = 'new';
        },
        close() {
            this.$refs.modal.close();
        },
        back() {
            this.issue = null;
            this.view = 'list';
        },
        'issue:selected': function(issue) {
            this.issue = issue;
            this.view = 'display';
        },
        'issue:created': function(issue) {
            this.issue = issue;
            this.view = 'display';
        },
        'issue:updated': function(issue) {
            this.issue = issue;
        }
    }
};
</script>
