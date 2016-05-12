<template>
    <datatable :title="title" icon="code-fork"
        boxclass="community-widget"
        :fields="fields"
        :p="communities"
        :empty="_('No community resources')">
    </datatable>
</template>

<script>
import Vue from 'vue';
import CommunityResources from 'models/communityresources';
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'community-widget',
    MASK: ['id', 'title', 'created_at', 'dataset{id,title}'],
    props: {
        communities: {
            type: Object,
            default() {
                return new CommunityResources();
            }
        },
        withoutDataset: Boolean,
        title: {
            type: String,
            default() {
                return this._('Community resources');
            }
        }
    },
    components: {Datatable},
    data() {
        let fields = [{
            label: this._('Title'),
            key: 'title',
            type: 'text'
        }, {
            label: this._('Created on'),
            key: 'created_at',
            type: 'datetime',
            width: 200
        }];
        if (!this.withoutDataset) {
            fields.push({
                label: this._('Dataset'),
                key: 'dataset.title',
                type: 'text',
                ellipsis: true
            });
        }
        return {fields};
    },
    events: {
        'datatable:item:click'(community) {
            const dataset_id = community.dataset ? community.dataset.id : 'deleted';
            this.$go({name: 'dataset-community-resource', params: {
                oid: dataset_id, rid: community.id
            }});
        }
    }
};
</script>
