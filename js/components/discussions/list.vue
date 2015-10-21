<template>
    <datatable title="{{ title }}" icon="comment"
        boxclass="discussions-widget"
        fields="{{ fields }}"
        p="{{ discussions }}"
        empty="{{ _('No discussion') }}">
    </datatable>
</template>


<script>
export default {
    name: 'discussions-widget',
    components: {
         'datatable': require('components/datatable/widget.vue')
    },
    data: function() {
        return {
            title: this.title || this._('Discussions'),
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
    props: ['discussions', 'title']
};
</script>
