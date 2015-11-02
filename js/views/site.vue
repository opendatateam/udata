<template>
    <div class="row">
        <sbox class="col-lg-3 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </sbox>
    </div>
    <div class="row">
        <chart title="Traffic" :metrics="metrics" class="col-xs-12"
            x="date" :y="y"></chart>
    </div>

    <div class="row">
        <datasets id="datasets" class="col-xs-12" :datasets="datasets"></datasets>
    </div>
    <div class="row">
        <reuses id="reuses" class="col-xs-12" :reuses="reuses"></reuses>
    </div>
    <div class="row">
        <organizations id="organizations" class="col-xs-12" :organizations="organizations"></organizations>
    </div>
    <div class="row">
        <users id="users" class="col-xs-12" :users="users"></users>
    </div>
    <div class="row">
        <issues class="col-xs-12 col-md-6" :issues="issues"></issues>
        <discussions class="col-xs-12 col-md-6" :discussions="discussions"></discussions>
    </div>
    <div class="row">
        <community class="col-xs-12" :communities="communities"></community>
    </div>
</template>

<script>
import moment from 'moment';

import Reuses from 'models/reuses';
import DatasetsFull from 'models/datasets_full';
import Metrics from 'models/metrics';
import Issues from 'models/issues';
import Discussions from 'models/discussions';
import Users from 'models/users';
import Organizations from 'models/organizations';
import CommunityResources from 'models/communityresources';

export default {
    name: 'SiteView',
    data: function() {
        return {
            metrics: new Metrics({
                data: {
                    loading: true,
                },
                query: {
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                }
            }),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}}),
            datasets: new DatasetsFull({query: {sort: '-created', page_size: 10}}),
            organizations: new Organizations({query: {sort: '-created', page_size: 10}}),
            users: new Users({query: {sort: '-created', page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            y: [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'reuses',
                label: this._('Reuses')
            }, {
                id: 'users',
                label: this._('Users'),
            }, {
                id: 'organizations',
                label: this._('Organizations')
            }]
        };
    },
    computed: {
        meta: function() {
            return {
                title: 'Site'
            };
        },
        boxes: function() {
            if (!this.$root.site.metrics) {
                return [];
            }
            return [{
                value: this.$root.site.metrics.datasets || 0,
                label: this._('Datasets'),
                icon: 'cubes',
                color: 'aqua',
                target: '#datasets'
            }, {
                value: this.$root.site.metrics.reuses || 0,
                label: this._('Reuses'),
                icon: 'retweet',
                color: 'green',
                target: '#reuses'
            }, {
                value: this.$root.site.metrics.users || 0,
                label: this._('Users'),
                icon: 'users',
                color: 'yellow',
                target: '#users'
            }, {
                value: this.$root.site.metrics.organizations || 0,
                label: this._('Organizations'),
                icon: 'building',
                color: 'purple',
                target: '#organizations'
            }];
        }
    },
    components: {
        sbox: require('components/containers/small-box.vue'),
        chart: require('components/charts/widget.vue'),
        datasets: require('components/dataset/list.vue'),
        reuses: require('components/reuse/list.vue'),
        organizations: require('components/organization/list.vue'),
        users: require('components/user/list.vue'),
        issues: require('components/issues/list.vue'),
        discussions: require('components/discussions/list.vue'),
        community: require('components/communityresource/list.vue'),
        posts: require('components/post/list.vue'),
        topics: require('components/topic/list.vue')
    },
    methods: {
        fetch_metrics: function() {
            if (this.$root.site.id) {
                this.metrics.fetch({id: this.$root.site.id});
            }
        }
    },
    attached: function() {
        this.fetch_metrics();
        this.datasets.fetch();
        this.reuses.fetch();
        this.users.fetch();
        this.issues.fetch();
        this.discussions.fetch();
        this.organizations.fetch();
        this.communities.fetch();
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        }
    },
    watch: {
        '$root.site.id': function() {
            this.fetch_metrics();
        }
    }
};
</script>
