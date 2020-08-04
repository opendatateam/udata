<template>
<div>
    <datatable :title="title" icon="cubes"
        boxclass="datasets-widget"
        :fields="fields" :p="datasets"
        :downloads="downloads"
        :empty="_('No dataset')">
    </datatable>
</div>
</template>

<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'dataset-list',
    components: {Datatable},
    MASK: ['id', 'title', 'acronym', 'created_at', 'last_update', 'last_modified', 'metrics', 'private', 'quality', 'archived'],
    data() {
        return {
            fields: [{
                label: this._('Title'),
                key(dataset) {
                    if (!dataset.acronym) return dataset.title;
                    return `${dataset.title} (${dataset.acronym})`;
                },
                sort: 'title',
                align: 'left',
                type: 'deletable-text'
            }, {
                label: this._('Creation'),
                key: 'created_at',
                sort: 'created',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Metadata update'),
                key: 'last_modified',
                sort: 'last_modified',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Data update'),
                key: 'last_update',
                sort: 'last_update',
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
            }, {
                label: this._('Quality'),
                key: 'quality.score',
                align: 'center',
                type: 'progress-bars',
                width: 125
            }]
        };
    },
    events: {
        'datatable:item:click': function(dataset) {
            this.$go(`/dataset/${dataset.id}/`);
        }
    },
    props: {
        datasets: null,
        downloads: {
            type: Array,
            default() {
                return [];
            }
        },
        title: {
            type: String,
            default() {
                return this._('Datasets');
            }
        }
    }
};
</script>
