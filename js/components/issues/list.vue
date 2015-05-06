<template>
    <datatable-widget title="{{ title }}" icon="warning" boxclass="issues-widget"
        fields="{{ fields }}" p="{{ issues }}">
    </datatable-widget>
</template>


<script>
'use strict';

module.exports = {
    name: 'issues-widget',
    components: {
         'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Issues'),
            fields: [{
                label: this._('ID'),
                key: 'id',
                type: 'text'
            }, {
                label: this._('Created on'),
                key: 'created',
                type: 'datetime'
            }]
        };
    },
    events: {
        'datatable:item:click': function(issue) {
            this.$go('/issue/' + issue.id + '/');
        }
    },
    paramAttributes: ['issues']
};
</script>
