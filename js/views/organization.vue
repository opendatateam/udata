<template>
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-repeat="boxes"></small-box>
    </div>
    <div class="row">
        <org-profile org="{{org}}" class="col-md-6"></org-profile>
        <org-members org="{{org}}" class="col-md-6"></org-members>
    </div>

    <div class="row">
        <morris-chart id="trafic-widget" class="col-xs-12"
            title="{{charts.traffic.title}}" default="{{charts.traffic.default}}"
            metrics="{{metrics}}"
            x="date" y="{{charts.traffic.y}}"
            >
        </morris-chart>
    </div>

    <div class="row">
        <datasets-widget id="datasets-widget" class="col-md-12" datasets="{{datasets}}"
         downloads="{{downloads}}">
        </datasets-widget>
    </div>

    <div class="row">
        <reuses-widget id="reuses-widget" class="col-md-12" reuses="{{reuses}}"></reuses-widget>
    </div>

    <div class="row">
        <followers-widget id="followers-widget" class="col-xs-12" followers="{{followers}}"></followers-widget>
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    URLs = require('urls'),
    List = require('models/base_page_list'),
    Organization = require('models/organization'),
    Datasets = require('models/datasets'),
    Reuses = require('models/reuses'),
    Followers = require('models/followers').extend({ns: 'organizations'}),
    Metrics = require('models/metrics');

module.exports = {
    name: 'OrganizationView',
    data: function() {
        return {
            org_id: null,
            org: new Organization(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new List({
                ns: 'organizations',
                fetch: 'list_organization_reuses',
            }),
            datasets: new List({
                ns: 'organizations',
                fetch: 'list_organization_datasets'
            }),
            followers: new Followers({query: {page_size: 10}}),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Organization'),
                actions: [{
                    label: this._('Delete'),
                    icon: 'trash',
                    method: 'confirm_delete'
                }]
            },
            charts: {
                traffic: {
                    title: this._('Traffic'),
                    default: 'Area',
                    y: [{
                        id: 'nb_uniq_visitors',
                        label: this._('Organization'),
                        color: '#3c8dbc'
                    }, {
                        id: 'datasets_nb_uniq_visitors',
                        label: this._('Datasets'),
                        color: '#a0d0e0'
                    }, {
                        id: 'reuses_nb_uniq_visitors',
                        label: this._('Reuses'),
                        color: '#8612EE'
                    }]
                },
                data: {
                    title: this._('Data'),
                    default: 'Bar',
                    y: [{
                        id: 'datasets',
                        label: this._('Datasets'),
                        color: '#3c8dbc'
                    }, {
                        id: 'reuses',
                        label: this._('Reuses'),
                        color: '#a0d0e0'
                    }]
                // }, {
                //     title: this._('Downloads'),
                //     type: 'Line',
                //     y: [{
                //         id: 'resources_downloads',
                //         label: this._('Resources'),
                //         color: '#3c8dbc'
                //     }]
                }
            }
        };
    },
    computed: {
        boxes: function() {
            if (!this.org.metrics) {
                return [];
            }
            return [{
                value: this.org.metrics.datasets || 0,
                label: this.org.metrics.datasets ? this._('Datasets') : this._('Dataset'),
                icon: 'cubes',
                color: 'aqua',
                target: '#datasets-widget'
            }, {
                value: this.org.metrics.reuses || 0,
                label: this.org.metrics.reuses ? this._('Reuses') : this._('Reuse'),
                icon: 'retweet',
                color: 'green',
                target: '#reuses-widget'
            }, {
                value: this.org.metrics.followers || 0,
                label: this.org.metrics.followers ? this._('Followers') : this._('Follower'),
                icon: 'users',
                color: 'yellow',
                target: '#followers-widget'
            }, {
                value: this.org.metrics.views || 0,
                label: this._('Views'),
                icon: 'eye',
                color: 'purple',
                target: '#trafic-widget'
            }];
        },
        downloads: function() {
            return [{
                label: this._('Datasets as CSV'),
                url: URLs.build('organization.datasets_csv', {org: this.org})
            }, {
                label: this._('Datasets resources as CSV'),
                url: URLs.build('organization.datasets_resources_csv', {org: this.org})
            }];
        }
    },
    components: {
        'small-box': require('components/containers/small-box.vue'),
        'org-profile': require('components/organization/profile.vue'),
        'org-members': require('components/organization/members.vue'),
        'morris-chart': require('components/charts/morris-chart.vue'),
        'datasets-widget': require('components/dataset/list.vue'),
        'reuses-widget': require('components/reuse/list.vue'),
        'followers-widget': require('components/follow/list.vue')
    },
    events: {
        'image:saved': function() {
            this.org.fetch();
        }
    },
    watch: {
        org_id: function(id) {
            if (id) {
                this.org.fetch(id);
            }
        },
        'org.name': function(name) {
            if (name) {
                this.meta.title = name;
                this.$dispatch('meta:updated', this.meta);

            }
        },
        'org.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({org: id});
                this.datasets.clear().fetch({org: id});
                this.followers.fetch({id: id});
            } else {
                this.datasets.clear();
                this.reuses.clear();
                this.followers.clear();
            }
        },
        'org.page': function(page) {
            if (page) {
                this.meta.page = page;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    }
};
</script>
