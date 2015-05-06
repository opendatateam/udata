<template>
    <datatable-widget title="{{ title }}" icon="retweet"
        boxclass="reuses-widget"
        fields="{{ fields }}" p="{{ reuses }}"
        downloads="{{downloads}}">
        <footer>
            <button type="button" class="btn btn-primary btn-sm"
                v-class="pull-right: reuses.pages > 1"
                v-route="/reuse/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable-widget>
</template>


<script>
'use strict';

module.exports = {
    name: 'reuses-widget',
    components: {
         'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Reuses'),
            fields: [{
                key: 'image',
                type: 'avatar',
                width: 30
            },{
                label: this._('Title'),
                key: 'title',
                sort: 'title',
                type: 'text'
            },{
                label: this._('Creation'),
                key: 'created_at',
                sort: 'created',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Modification'),
                key: 'last_modified',
                sort: 'last_modified',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Datasets'),
                key: 'metrics.datasets',
                sort: 'datasets',
                align: 'center',
                type: 'metric',
                width: 135
            }, {
                label: this._('Followers'),
                key: 'metrics.followers',
                sort: 'followers',
                align: 'center',
                type: 'metric',
                width: 95
            }, {
                label: this._('Views'),
                key: 'metrics.views',
                sort: 'views',
                align: 'center',
                type: 'metric',
                width: 95
            }]
        };
    },
    events: {
        'datatable:item:click': function(reuse) {
            this.$go('/reuse/' + reuse.id + '/');
        }
    },
    paramAttributes: ['reuses', 'downloads']
};
</script>
