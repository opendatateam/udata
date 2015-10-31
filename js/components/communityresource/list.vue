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
         'datatable': require('components/datatable/widget.vue')
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
    ready: function() {
        /* In case of a targeted community resource,
           we display the appropriated popin on load. */
        if ('community_id' in this.$route.params) {
            this.display(this.$route.params['community_id']);
        }
    },
    methods: {
        display: function(communityId) {
            this.community.fetch(communityId);
            this.$root.$modal({
                    data: {
                        community: this.community,
                        dataset: this.community.dataset,
                        callback: this.refresh,
                    }
                },
                Vue.extend(require('components/communityresource/edit-modal.vue'))
            );
        },
        refresh: function() {
            this.communities.fetch();
        }
    },
    events: {
        'datatable:item:click': function(community) {
            if (community.organization) {
                this.$go('/organization/' + community.organization.id + '/?community_id=' + community.id);
            } else {
                this.$go('/user/' + community.owner.id + '/?community_id=' + community.id);
            }
            this.display(community.id);
        }
    }
};
</script>
