<template>
    <datatable-widget title="{{ title }}" icon="book" boxclass="topics-widget"
        fields="{{ fields }}" p="{{ topics }}">
        <footer>
            <button type="button" class="btn btn-primary btn-flat btn-sm"
                v-class="pull-right: topics.pages > 1"
                v-route="/topic/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable-widget>
</template>



<script>
'use strict';

module.exports = {
    name: 'topics-widget',
    components: {
         'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Topics'),
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                type: 'text'
            // },{
            //     label: this._('Creation'),
            //     key: 'created_at',
            //     sort: 'created',
            //     align: 'left',
            //     type: 'timeago',
            //     width: 120
            // }, {
            //     label: this._('Modification'),
            //     key: 'last_modified',
            //     sort: 'last_modified',
            //     align: 'left',
            //     type: 'timeago',
            //     width: 120
            }]
        };
    },
    events: {
        'datatable:item:click': function(topic) {
            this.$go('/topic/' + topic.id + '/');
        }
    },
    props: ['topics']
};
</script>
