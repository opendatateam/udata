<template>
    <datatable :title="title" icon="comment"
        boxclass="discussions-widget"
        :fields="fields"
        :p="discussions"
        :empty="_('No discussion')">
    </datatable>
</template>


<script>
export default {
    name: 'discussions-widget',
    components: {
         datatable: require('components/datatable/widget.vue')
    },
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
        'datatable:item:click': function(discussion) {
            this.$go('/discussion/' + discussion.id + '/');
        }
    },
    props: {
        discussions: null,
        title: {
            type: String,
            default: function() {
                return this._('Discussions');
            }
        }
    }
};
</script>
