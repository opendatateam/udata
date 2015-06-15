<template>
    <datatable title="{{ title }}" icon="warning"
        boxclass="issues-widget"
        fields="{{ fields }}"
        p="{{ issues }}"
        empty="{{ _('No issues') }}">
    </datatable>
</template>


<script>
'use strict';

module.exports = {
    name: 'issues-widget',
    components: {
         'datatable': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Issues'),
            fields: [{
                label: this._('Title'),
                key: 'title',
                type: 'text'
            }, {
                label: this._('Created on'),
                key: 'created',
                type: 'datetime'
            }, {
                label: this._('Closed on'),
                key: 'closed',
                type: 'datetime'
            }]
        };
    },
    events: {
        'datatable:item:click': function(issue) {
            this.$go('/issue/' + issue.id + '/');
        }
    },
    props: ['issues']
};
</script>
