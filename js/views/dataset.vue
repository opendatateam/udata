<template>
    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-repeat="boxes"></small-box>
    </div>
    <div class="row">
        <div class="col-xs-12 col-md-6">
            <dataset-details dataset="{{dataset}}"></dataset-details>
            <map-widget title="{{ _('Spatial coverage') }}"
                geojson="{{geojson}}"></map-widget>
        </div>
        <dataset-quality quality="{{ dataset.quality }}" class="col-xs-12 col-md-6"></dataset-quality>
    </div>
    <div class="row">
        <resources-list dataset="{{dataset}}" class="col-xs-12"></resources-list>
    </div>
    <div class="row">
        <chart id="trafic-widget" class="col-xs-12" title="{{ _('Audience') }}"
            metrics="{{metrics}}" x="date" y="{{y}}"></chart>
    </div>

    <div class="row">
        <reuses-widget id="reuses-widget" class="col-xs-12" reuses="{{reuses}}"></reuses-widget>
    </div>

    <div class="row">
        <issues-widget id="issues-widget" class="col-xs-12" issues="{{issues}}"></issues-widget>
    </div>

    <div class="row">
        <discussions id="discussions-widget" class="col-xs-12" discussions="{{discussions}}"></discussions>
    </div>

    <div class="row">
        <followers-widget id="followers-widget" class="col-xs-12 col-md-6" followers="{{followers}}"></followers-widget>
    </div>

</template>

<script>
import API from 'api';
import Dataset from 'models/dataset';
import Discussions from 'models/discussions';
import Followers from 'models/followers';
import Issues from 'models/issues';
import Metrics from 'models/metrics';
import moment from 'moment';
import Reuses from 'models/reuses';
import Vue from 'vue';

export default {
    name: 'DatasetView',
    data: function() {
        var actions = [{
                label: this._('Transfer'),
                icon: 'send',
                method: 'transfer_request'
            },{
                label: this._('Delete'),
                icon: 'trash',
                method: 'confirm_delete'
            }];

        if (this.$root.me.is_admin) {
            actions.push({divider: true});
            actions.push({
                label: this._('Badges'),
                icon: 'bookmark',
                method: 'setBadges'
            });
        }

        return {
            dataset_id: null,
            dataset: new Dataset(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}}),
            followers: new Followers({ns: 'datasets', query: {page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}}),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Dataset'),
                actions: actions,
                badges:  []
            },
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
            notifications: [],
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
                target: '#reuses-widget'
            }, {
                value: this.dataset.metrics.followers || 0,
                label: this.dataset.metrics.followers ? this._('Followers') : this._('Follower'),
                icon: 'users',
                color: 'yellow',
                target: '#followers-widget'

            }, {
                value: this.dataset.metrics.views || 0,
                label: this._('Views'),
                icon: 'eye',
                color: 'purple',
                target: '#trafic-widget'
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
        'small-box': require('components/containers/small-box.vue'),
        'dataset-details': require('components/dataset/details.vue'),
        'dataset-quality': require('components/dataset/quality.vue'),
        'chart': require('components/charts/widget.vue'),
        'resources-list': require('components/dataset/resources-list.vue'),
        'reuses-widget': require('components/reuse/list.vue'),
        'followers-widget': require('components/follow/list.vue'),
        'map-widget': require('components/widgets/map.vue'),
        'issues-widget': require('components/issues/list.vue'),
        'discussions': require('components/discussions/list.vue'),
    },
    methods: {
        confirm_delete: function() {
            var m = this.$root.$modal(
                {data: {dataset: this.dataset}},
                Vue.extend(require('components/dataset/delete-modal.vue'))
            );
        },
        transfer_request: function() {
            this.$root.$modal(
                {data: {subject: this.dataset}},
                Vue.extend(require('components/transfer/request-modal.vue'))
            );
        },
        setBadges: function() {
            this.$root.$modal(
                {data: {subject: this.dataset}},
                Vue.extend(require('components/badges/modal.vue'))
            );
        }
    },
    watch: {
        dataset_id: function(id) {
            if (id) {
                this.dataset.fetch(id);
            }
        },
        'dataset.title': function(title) {
            if (title) {
                this.meta.title = title;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'dataset.page': function(page) {
            if (page) {
                this.meta.page = page;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'dataset.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({dataset: id});
                this.followers.fetch({id: id});
                this.issues.fetch({'for': id});
                this.discussions.fetch({'for': id});
            } else {
                this.reuses.clear();
                this.followers.clear();
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
                API.spatial.spatial_zones({ids: coverage.zones}, function(response) {
                    this.geojson = response.obj;
                }.bind(this));
            }
        },
        'dataset.deleted': function(deleted) {
            if (deleted) {
                this.meta.badges = [{
                    class: 'danger',
                    label: this._('Deleted')
                }];
            }
        }
    }
};
</script>
