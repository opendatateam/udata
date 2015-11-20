<template>
<layout :title="dataset.title || ''" :subtitle="_('Dataset')"
    :actions="actions" :badges="badges" :page="dataset.page || ''">
    <div class="row">
        <sbox class="col-lg-4 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </sbox>
    </div>
    <div class="row">
        <div class="col-xs-12 col-md-6">
            <dataset :dataset="dataset"></dataset>
            <wmap :title="_('Spatial coverage')" :geojson="geojson"></wmap>
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
        <reuses id="reuses" class="col-xs-12" :reuses="reuses"></reuses>
    </div>

    <div class="row">
        <issues class="col-xs-12" :issues="issues"></issues>
    </div>

    <div class="row">
        <discussions class="col-xs-12" :discussions="discussions"></discussions>
    </div>

    <div class="row">
        <followers id="followers" class="col-xs-12 col-md-6" :followers="followers"></followers>
        <community class="col-xs-12 col-md-6" :communities="communities" :without-dataset="true"></community>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import API from 'api';
import Vue from 'vue';
import DatasetFull from 'models/dataset_full';
import Discussions from 'models/discussions';
import Followers from 'models/followers';
import Issues from 'models/issues';
import Metrics from 'models/metrics';
import Reuses from 'models/reuses';
import CommunityResources from 'models/communityresources';
import Layout from 'components/layout.vue';

export default {
    name: 'DatasetView',
    data: function() {
        var actions = [{
                label: this._('Transfer'),
                icon: 'send',
                method: this.transfer_request
            },{
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
            dataset: new DatasetFull(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}}),
            followers: new Followers({ns: 'datasets', query: {page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
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
        boxes: function() {
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
        }
        // coverage: function() {
        //     if (!this.dataset.spatial || !this.dataset.spatial.geom) {
        //         return null;
        //     }
        //     return this.dataset.spatial.geom;
        // }
    },
    components: {
        sbox: require('components/containers/small-box.vue'),
        dataset: require('components/dataset/details.vue'),
        quality: require('components/dataset/quality.vue'),
        chart: require('components/charts/widget.vue'),
        resources: require('components/dataset/resources-list.vue'),
        reuses: require('components/reuse/list.vue'),
        followers: require('components/follow/list.vue'),
        wmap: require('components/widgets/map.vue'),
        issues: require('components/issues/list.vue'),
        discussions: require('components/discussions/list.vue'),
        community: require('components/communityresource/list.vue'),
        Layout
    },
    methods: {
        confirm_delete: function() {
            var m = this.$root.$modal(
                require('components/dataset/delete-modal.vue'),
                {dataset: this.dataset}
            );
        },
        transfer_request: function() {
            this.$root.$modal(
                require('components/transfer/request-modal.vue'),
                {subject: this.dataset}
            );
        },
        setBadges: function() {
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
