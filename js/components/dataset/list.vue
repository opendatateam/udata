<template>
    <datatable-widget title="{{ title }}" icon="cubes"
        boxclass="datasets-widget"
        fields="{{ fields }}" p="{{ datasets }}"
        downloads="{{downloads}}">
        <footer>
            <button type="button" class="btn btn-primary btn-sm btn-flat"
                v-class="pull-right: datasets.pages > 1"
                v-route="/dataset/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable-widget>
</template>

<script>
'use strict';

module.exports = {
    name: 'datasets-widget',
    components: {
        'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Datasets'),
            fields: [{
                label: this._('Title'),
                key: 'title',
                sort: 'title',
                align: 'left',
                type: 'text'
            }, {
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
                label: this._('Reuses'),
                key: 'metrics.reuses',
                sort: 'reuses',
                align: 'center',
                type: 'metric',
                width: 125
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
        'datatable:item:click': function(dataset) {
            this.$go('/dataset/' + dataset.id + '/');
        }
    },
    paramAttributes: ['datasets', 'downloads']
};
</script>
