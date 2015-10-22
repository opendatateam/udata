<template>
    <datatable title="{{ title }}" icon="warning"
        boxclass="issues-widget"
        fields="{{ fields }}"
        p="{{ issues }}"
        empty="{{ _('No issues') }}">
    </datatable>
</template>


<script>
export default {
    name: 'issues-widget',
    components: {
         'datatable': require('components/datatable/widget.vue')
    },
    data: function() {
        return {
            title: this.title || this._('Issues'),
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
            this.$go('/issue/' + issue.id + '/');
        }
    },
    props: ['issues', 'title']
};
</script>
