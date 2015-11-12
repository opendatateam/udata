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
import CommunityResource from 'models/communityresource';
import CommunityResources from 'models/communityresources';

export default {
    name: 'community-widget',
    props: {
        communities: {
            type: Object,
            default: function() {
                return new CommunityResources();
            }
        },
        withoutDataset: Boolean
    },
    components: {
         datatable: require('components/datatable/widget.vue')
    },
    data: function() {
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
        return {
            title: this._('Community resources'),
            fields: fields,
            community: new CommunityResource(),
        };
    },
    events: {
        'datatable:item:click': function(community) {
            this.$go({name: 'dataset-community-resource', params: {
                oid: community.dataset.id, rid: community.id
            }});
        }
    }
};
</script>
