<template>
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-repeat="boxes"></small-box>
    </div>
    <div class="row">
        <morris-chart title="Traffic" metrics="{{metrics}}" class="col-md-12"
            x="date" y="{{y}}"></morris-chart>
    </div>

    <div class="row">
        <datasets-widget id="datasets-widget" class="col-md-12" datasets="{{datasets}}"></datasets-widget>
    </div>
    <div class="row">
        <reuses-widget id="reuses-widget" class="col-md-12" reuses="{{reuses}}"></reuses-widget>
    </div>
    <div class="row">
        <organizations-widget id="organizations-widget" class="col-md-12" organizations="{{organizations}}"></organizations-widget>
    </div>
    <div class="row">
        <users-widget id="users-widget" class="col-md-12" users="{{users}}"></users-widget>
    </div>
    <div class="row">
        <issues-widget id="issues-widget" class="col-md-12" issues="{{issues}}"></issues-widget>
    </div>
    <div class="row">
        <discussions-widget id="discussions-widget" class="col-md-12" discussions="{{discussions}}"></discussions-widget>
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    Reuses = require('models/reuses'),
    Datasets = require('models/datasets'),
    Metrics = require('models/metrics'),
    Issues = require('models/issues'),
    Discussions = require('models/discussions'),
    Users = require('models/users'),
    Organizations = require('models/organizations');

module.exports = {
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
            datasets: new Datasets({query: {sort: '-created', page_size: 10}}),
            organizations: new Organizations({query: {sort: '-created', page_size: 10}}),
            users: new Users({query: {sort: '-created', page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}}),
            y: [{
                id: 'datasets',
                label: this._('Datasets'),
                color: '#a0d0e0'
            }, {
                id: 'reuses',
                label: this._('Reuses'),
                color: '#3c8dbc'
            }, {
                id: 'users',
                label: this._('Users'),
                color: '#aaa'
            }, {
                id: 'organizations',
                label: this._('Organizations'),
                color: '#3c8dbc'
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
                target: '#datasets-widget'
            }, {
                value: this.$root.site.metrics.reuses || 0,
                label: this._('Reuses'),
                icon: 'retweet',
                color: 'green',
                target: '#reuses-widget'
            }, {
                value: this.$root.site.metrics.users || 0,
                label: this._('Users'),
                icon: 'users',
                color: 'yellow',
                target: '#users-widget'
            }, {
                value: this.$root.site.metrics.organizations || 0,
                label: this._('Organizations'),
                icon: 'building',
                color: 'purple',
                target: '#organizations-widget'
            }];
        }
    },
    components: {
        'small-box': require('components/containers/small-box.vue'),
        'morris-chart': require('components/charts/morris-chart.vue'),
        'datasets-widget': require('components/dataset/list.vue'),
        'reuses-widget': require('components/reuse/list.vue'),
        'organizations-widget': require('components/organization/list.vue'),
        'users-widget': require('components/user/list.vue'),
        'issues-widget': require('components/issues/list.vue'),
        'discussions-widget': require('components/discussions/list.vue'),
        'posts-widget': require('components/post/list.vue'),
        'topics-widget': require('components/topic/list.vue')
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
    },
    watch: {
        '$root.site.id': function() {
            this.fetch_metrics();
        }
    }
};
</script>
