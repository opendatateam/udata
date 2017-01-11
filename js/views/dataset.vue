<template>
<layout :title="dataset.title || ''" :subtitle="_('Dataset')"
    :actions="actions" :badges="badges" :page="dataset.page || ''">
    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </small-box>
    </div>
    <div class="row">
        <div class="col-xs-12 col-md-6">
            <dataset :dataset="dataset"></dataset>
            <wmap :title="_('Spatial coverage')" :geojson="geojson" :footer="map_footer">
                <ul>
                    <li v-show="dataset.spatial && dataset.spatial.granularity">
                        <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                            :title="_('Territorial coverage granularity')">
                            <span class="fa fa-bullseye fa-fw"></span>
                            {{ dataset | granularity_label }}
                        </a>
                    </li>
                    <li v-show="territories_labels">
                        <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                            :title="_('Territorial coverage')">
                            <span class="fa fa-map-marker fa-fw"></span>
                            {{ territories_labels }}
                        </a>
                    </li>
                </ul>
            </wmap>
        </div>
        <quality :quality="dataset.quality" class="col-xs-12 col-md-6"></quality>
    </div>
    <div class="row">
        <resources :dataset="dataset" class="col-xs-12"></resources>
    </div>
    <div class="row">
        <chart id="trafic" class="col-xs-12" :title="_('Audience')"
            :metrics="metrics" x="date" :y="y"></chart>
    </div>

    <div class="row">
        <reuse-list id="reuses" class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>

    <div class="row">
        <issue-list class="col-xs-12" :issues="issues"></issue-list>
    </div>

    <div class="row">
        <discussion-list class="col-xs-12" :discussions="discussions"></discussion-list>
    </div>

    <div class="row">
        <followers id="followers" class="col-xs-12 col-md-6" :followers="followers"></followers>
        <community-list class="col-xs-12 col-md-6" :communities="communities" :without-dataset="true"></community-list>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import API from 'api';
import Vue from 'vue';
import Dataset from 'models/dataset';
import Discussions from 'models/discussions';
import Followers from 'models/followers';
import Issues from 'models/issues';
import Metrics from 'models/metrics';
import Reuses from 'models/reuses';
import CommunityResources from 'models/communityresources';
// Widgets
import CommunityList from 'components/dataset/communityresource/list.vue';
import DiscussionList from 'components/discussions/list.vue';
import IssueList from 'components/issues/list.vue';
import Layout from 'components/layout.vue';
import DatasetFilters from 'components/dataset/filters';
import ReuseList from 'components/reuse/list.vue';
import SmallBox from 'components/containers/small-box.vue';

export default {
    name: 'DatasetView',
    mixins: [DatasetFilters],
    data: function() {
        var actions = [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
            }, {
                label: this._('Transfer'),
                icon: 'send',
                method: this.transfer_request
            }, {
                label: this._('Delete'),
                icon: 'trash',
                method: this.confirm_delete
            }];

        if (this.$root.me.is_admin) {
            actions.push({divider: true});
            actions.push({
                label: this._('Badges'),
                icon: 'bookmark',
                method: this.setBadges
            });
        }

        return {
            dataset: new Dataset({mask: '*'}),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}, mask: ReuseList.MASK}),
            followers: new Followers({ns: 'datasets', query: {page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}, mask: IssueList.MASK}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}, mask: DiscussionList.MASK}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}, mask: CommunityList.MASK}),
            actions: actions,
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
            geojson: null
        };
    },
    computed: {
        boxes() {
            if (!this.dataset.metrics) {
                return [];
            }
            return [{
                value: this.dataset.metrics.reuses || 0,
                label: this.dataset.metrics.reuses ? this._('Reuses') : this._('Reuse'),
                icon: 'retweet',
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
        territories_labels() {
            if (this.geojson && this.geojson.features) {
                return this.geojson.features.map(feature => feature.properties.name).join(', ');
            }
        },
        map_footer() {
            return (this.dataset.spatial && this.dataset.spatial.granularity || this.territories_labels) !== undefined;
        }
    },
    components: {
        dataset: require('components/dataset/details.vue'),
        quality: require('components/dataset/quality.vue'),
        chart: require('components/charts/widget.vue'),
        resources: require('components/dataset/resource/list.vue'),
        followers: require('components/follow/list.vue'),
        wmap: require('components/widgets/map.vue'),
        CommunityList,
        DiscussionList,
        SmallBox,
        ReuseList,
        IssueList,
        Layout
    },
    methods: {
        edit() {
            this.$go({name: 'dataset-edit', params: {oid: this.dataset.id}});
        },
        confirm_delete() {
            var m = this.$root.$modal(
                require('components/dataset/delete-modal.vue'),
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
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({dataset: id});
                this.followers.fetch({id: id});
                this.issues.fetch({'for': id});
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
                this.geojson = null;
                return;
            }
            if (coverage.geom) {
                this.geojson = coverage.geom
            } else {
                API.spatial.spatial_zones({ids: coverage.zones}, (response) => {
                    this.geojson = response.obj;
                });
            }
        },
        'dataset.deleted': function(deleted) {
            if (deleted) {
                this.badges = [{
                    class: 'danger',
                    label: this._('Deleted')
                }];
            }
        }
    }
};
</script>
