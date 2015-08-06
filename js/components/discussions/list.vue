<template>
    <datatable title="{{ title }}" icon="comment"
        boxclass="discussions-widget"
        fields="{{ fields }}"
        p="{{ discussions }}"
        empty="{{ _('No discussion') }}">
    </datatable>
</template>


<script>
'use strict';

module.exports = {
    name: 'discussions-widget',
    components: {
         'datatable': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Discussions'),
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
        'datatable:item:click': function(discussion) {
            this.$go('/discussion/' + discussion.id + '/');
        }
    },
    props: ['discussions']
};
</script>
