<template>
    <datatable-widget title="{{ title }}" icon="comment" boxclass="discussions-widget"
        fields="{{ fields }}" p="{{ discussions }}">
    </datatable-widget>
</template>


<script>
'use strict';

module.exports = {
    name: 'discussions-widget',
    components: {
         'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Discussions'),
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
        'datatable:item:click': function(discussion) {
            this.$go('/discussion/' + discussion.id + '/');
        }
    },
    props: ['discussions']
};
</script>
