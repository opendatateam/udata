<template>
    <datatable title="{{ title }}" icon="cubes"
        boxclass="datasets-widget"
        fields="{{ fields }}" p="{{ datasets }}"
        downloads="{{downloads}}"
        empty="{{ _('No dataset') }}">
    </datatable>
</template>

<script>
export default {
    name: 'datasets-widget',
    components: {
        'datatable': require('components/widgets/datatable.vue')
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
            }, {
                label: this._('Status'),
                align: 'center',
                type: 'visibility',
                width: 95
            }],
            downloads: []
        };
    },
    events: {
        'datatable:item:click': function(dataset) {
            this.$go('/dataset/' + dataset.id + '/');
        }
    },
    props: ['datasets', 'downloads']
};
</script>
