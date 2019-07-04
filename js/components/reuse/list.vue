<template>
<div>
    <datatable :title="title" icon="recycle"
        boxclass="reuses-widget"
        :fields="fields" :p="reuses"
        :downloads="downloads"
        :empty="_('No reuse')">
    </datatable>
</div>
</template>


<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'reuses-list',
    components: {Datatable},
    MASK: ['id', 'title', 'created_at', 'last_modified', 'metrics', 'private', 'image_thumbnail'],
    data() {
        return {
            fields: [{
                key: 'image_thumbnail',
                type: 'thumbnail',
                width: 30
            },{
                label: this._('Title'),
                key: 'title',
                sort: 'title',
                type: 'deletable-text'
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
            }, {
                label: this._('Status'),
                align: 'center',
                type: 'visibility',
                width: 95
            }]
        };
    },
    events: {
        'datatable:item:click'(reuse) {
            this.$go('/reuse/' + reuse.id + '/');
        }
    },
    props: {
        reuses: null,
        downloads: {
            type: Array,
            default() {
                return [];
            }
        },
        title: {
            type: String,
            default() {
                return this._('Reuses');
            }
        }
    }
};
</script>
