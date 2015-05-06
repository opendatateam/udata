<template>
    <datatable-widget title="{{ title }}" icon="tasks"
        boxclass="harvest-jobs-widget"
        fields="{{ fields }}"
        p="{{ jobs }}">
    </datatable-widget>
</template>

<script>
'use strict';

var Vue = require('vue');

var LABELS_TYPE = {
    'pending': 'default',
    'initializing': 'primary',
    'initialized': 'info',
    'processing': 'info',
    'done': 'success',
    'done-errors': 'warning',
    'failed': 'danger'
};

module.exports = {
    name: 'harvest-jobs-widget',
    components: {
        'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: Vue._('Jobs'),
            fields: [{
                label: this._('Date'),
                key: 'created',
                sort: 'created',
                type: 'datetime'
            }, {
                label: this._('Status'),
                key: 'status',
                type: 'label',
                label_type: function(status) {
                    return LABELS_TYPE[status];
                }
            }]
        };
    },
    events: {
        'datatable:item:click': function(item) {
            this.$dispatch('harvest:job:selected', item);
        }
    },
    paramAttributes: ['jobs', 'current']
};
</script>
