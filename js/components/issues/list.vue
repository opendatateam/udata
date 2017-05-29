<template>
<div>
    <datatable :title="title" icon="warning"
        boxclass="issues-widget"
        :fields="fields"
        :p="issues"
        :empty="_('No issues')">
    </datatable>
</div>
</template>

<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'issues-list',
    components: {Datatable},
    MASK: ['id', 'class', 'title', 'created', 'closed', 'subject'],
    data() {
        return {
            fields: [{
                label: this._('Title'),
                key: 'title',
                type: 'text',
                ellipsis: true
            }, {
                label: this._('Created on'),
                key: 'created',
                type: 'datetime',
                width: 200
            }, {
                label: this._('Closed on'),
                key: 'closed',
                type: 'datetime',
                width: 200
            }]
        };
    },
    events: {
        'datatable:item:click': function(issue) {
            const prefix = issue.subject.class.toLowerCase();
            const route = `${prefix}-issue`;
            this.$go({name: route, params: {
                oid: issue.subject.id,
                issue_id: issue.id
            }});
        }
    },
    props: {
        issues: null,
        title: {
            type: String,
            default() {return this._('Issues')},
        }
    }
};
</script>
