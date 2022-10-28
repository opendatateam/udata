<template>
<div>
<layout :title="dataset.full_title || ''" :subtitle="_('Dataset')"
    :actions="actions" :badges="badges" :page="dataset.page || ''">
    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </small-box>
    </div>
    <div class="row">
        <div class="col-xs-12 col-md-6">
            <dataset-details :dataset="dataset" :spatial-coverage="spatialCoverage"></dataset-details>
        </div>
        <quality-widget :quality="dataset.quality" class="col-xs-12 col-md-6"></quality-widget>
    </div>
    <div class="row">
        <resource-list :dataset="dataset" class="col-xs-12"></resource-list>
    </div>

    <div class="row">
        <reuse-list id="reuses" class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>

    <div class="row">
        <discussion-list class="col-xs-12" :discussions="discussions"></discussion-list>
    </div>

    <div class="row">
        <follower-list id="followers" class="col-xs-12 col-md-6" :followers="followers"></follower-list>
        <community-list class="col-xs-12 col-md-6" :communities="communities" :without-dataset="true"></community-list>
    </div>
</layout>
</div>
</template>

<script>
import API from 'api';
import {ModelPage} from 'models/base';
import Dataset from 'models/dataset';
import Discussions from 'models/discussions';
import Reuses from 'models/reuses';
import CommunityResources from 'models/communityresources';
// Widgets
import ChartWidget from 'components/charts/widget.vue';
import CommunityList from 'components/dataset/communityresource/list.vue';
import DatasetDetails from 'components/dataset/details.vue';
import DatasetFilters from 'components/dataset/filters';
import DiscussionList from 'components/discussions/list.vue';
import FollowerList from 'components/follow/list.vue';
import Layout from 'components/layout.vue';
import QualityWidget from 'components/dataset/quality.vue';
import ResourceList from 'components/dataset/resource/list.vue';
import ReuseList from 'components/reuse/list.vue';
import SmallBox from 'components/containers/small-box.vue';

export default {
    name: 'dataset-view',
    mixins: [DatasetFilters],
    components: {
        ChartWidget,
        CommunityList,
        DatasetDetails,
        DiscussionList,
        FollowerList,
        Layout,
        QualityWidget,
        ResourceList,
        ReuseList,
        SmallBox,
    },
    data() {
        return {
            dataset: new Dataset({mask: '*'}),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}, mask: ReuseList.MASK}),
            followers: new ModelPage({
                query: {page_size: 10},
                ns: 'datasets',
                fetch: 'list_dataset_followers'
            }),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}, mask: DiscussionList.MASK}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}, mask: CommunityList.MASK}),
            badges:  [],
            y: [{
                id: 'views',
                label: this._('Views')
            }, {
                id: 'followers',
                label: this._('Followers')
            }],
            y_visitors: [{
                id: 'views',
                label: this._('Hits')
            }, {
                id: 'followers',
                label: this._('Unique visitors')
            }],
            spatialCoverage: []
        };
    },
    computed: {
        actions() {
            const actions = [];
            if (this.can_edit) {
                actions.push({
                    label: this._('Edit this dataset'),
                    icon: 'edit',
                    method: this.edit
                }, {
                    label: this._('Transfer'),
                    icon: 'send',
                    method: this.transfer_request
                });
                if(!this.dataset.deleted) {
                    actions.push({
                        label: this._('Delete'),
                        icon: 'trash',
                        method: this.confirm_delete
                    });
                } else {
                    actions.push({
                        label: this._('Restore'),
                        icon: 'undo',
                        method: this.confirm_restore
                    });
                }
            }

            if (this.$root.me.is_admin) {
                actions.push({divider: true});
                actions.push({
                    label: this._('Badges'),
                    icon: 'bookmark',
                    method: this.setBadges
                });
            }
            return actions;
        },
        boxes() {
            if (!this.dataset.metrics) {
                return [];
            }
            return [{
                value: this.dataset.metrics.reuses || 0,
                label: this.dataset.metrics.reuses ? this._('Reuses') : this._('Reuse'),
                icon: 'recycle',
                color: 'green',
                target: '#reuses'
            }, {
                value: this.dataset.metrics.followers || 0,
                label: this.dataset.metrics.followers ? this._('Followers') : this._('Follower'),
                icon: 'users',
                color: 'yellow',
                target: '#followers'

            }, {
                value: this.dataset.metrics.views || 0,
                label: this._('Views'),
                icon: 'eye',
                color: 'purple',
                target: '#trafic'
            }];
        },
        can_edit() {
            return this.$root.me.can_edit(this.dataset);
        }
    },
    methods: {
        edit() {
            this.$go({name: 'dataset-edit', params: {oid: this.dataset.id}});
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/dataset/delete-modal.vue'),
                {dataset: this.dataset}
            );
        },
        confirm_restore() {
            this.$root.$modal(
                require('components/dataset/restore-modal.vue'),
                {dataset: this.dataset}
            );
        },
        transfer_request() {
            this.$root.$modal(
                require('components/transfer/request-modal.vue'),
                {subject: this.dataset}
            );
        },
        setBadges() {
            this.$root.$modal(
                require('components/badges/modal.vue'),
                {subject: this.dataset}
            );
        },
        addOrRemoveBadge(id, value, _class, label) {
            const existing = this.badges.find(b => b.id === id);
            if (value && !existing) {
                this.badges.push({
                    id,
                    class: _class,
                    label
                });
            } else if (existing) {
                this.badges.splice(this.badges.indexOf(existing), 1);
            }
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.dataset.id) {
                this.dataset.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    },
    watch: {
        'dataset.id': function(id) {
            if (id) {
                this.reuses.clear().fetch({dataset: id});
                this.followers.fetch({id: id});
                this.discussions.fetch({'for': id});
                this.communities.clear().fetch({dataset: id});
            } else {
                this.reuses.clear();
                this.followers.clear();
                this.communities.clear();
            }
        },
        'dataset.spatial': function(coverage) {
            if (!coverage || !(coverage.geom || coverage.zones.length)) {
                return;
            }
            if (coverage.geom) {
                this.spatialCoverage.push(this._('Custom'));
            }
            if (coverage.zones) {
                coverage.zones.forEach(zone => {
                    API.spatial.spatial_zone({id: zone}, (response) => {
                        this.spatialCoverage.push(response.obj.properties.name);
                    });
                });
            }
        },
        'dataset.deleted': function(deleted) {
            this.addOrRemoveBadge('deleted', deleted, 'danger', this._('Deleted'));
        },
        'dataset.archived': function(archived) {
            this.addOrRemoveBadge('archived', archived, 'warning', this._('Archived'));
        }
    }
};
</script>
