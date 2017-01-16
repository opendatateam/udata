<template>
    <datatable :title="title" icon="warning"
        boxclass="issues-widget"
        :fields="fields"
        :p="issues"
        :empty="_('No issues')">
    </datatable>
</template>


<script>
export default {
    name: 'issues-widget',
    components: {
         datatable: require('components/datatable/widget.vue')
    },
    MASK: ['id', 'class', 'title', 'created', 'closed', 'subject'],
    data: function() {
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
            let prefix = issue.subject.class.toLowerCase(),
                route = `${prefix}-issue`;
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
            default: function() {
                return this._('Issues');
            }
        }
    }
};
</script>
