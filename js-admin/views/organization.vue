<template>
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-repeat="boxes"></small-box>
    </div>
    <div class="row">
        <org-profile org="{{org}}" class="col-xs-12 col-md-6"></org-profile>
        <org-members org="{{org}}" class="col-xs-12 col-md-6"></org-members>
    </div>

    <div class="row">
        <chart id="trafic-widget" class="col-xs-12"
            title="{{charts.traffic.title}}" default="{{charts.traffic.default}}"
            metrics="{{metrics}}"
            x="date" y="{{charts.traffic.y}}"
            >
        </chart>
    </div>

    <div class="row">
        <datasets-widget id="datasets-widget" class="col-xs-12" datasets="{{datasets}}"
         downloads="{{downloads}}">
        </datasets-widget>
    </div>

    <div class="row">
        <reuses-widget id="reuses-widget" class="col-xs-12" reuses="{{reuses}}"></reuses-widget>
    </div>

    <div class="row">
        <issues id="issues-widget" class="col-xs-12" issues="{{issues}}"></issues>
    </div>

    <div class="row">
        <discussions id="discussions-widget" class="col-xs-12" discussions="{{discussions}}"></discussions>
    </div>

    <div class="row">
        <followers-widget id="followers-widget" class="col-xs-12" followers="{{followers}}"></followers-widget>
    </div>
</template>

<script>
import Datasets from 'models/datasets';
import Followers from 'models/followers';
import Metrics from 'models/metrics';
import moment from 'moment';
import Organization from 'models/organization';
import Reuses from 'models/reuses';
import URLs from 'urls';
import Vue from 'vue';
import {PageList} from 'models/base';

export default {
    name: 'OrganizationView',
    data: function() {
        var actions = [{
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
            org_id: null,
            org: new Organization(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_reuses',
                search: 'title'
            }),
            datasets: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_datasets',
                search: 'title'
            }),
            issues: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_issues',
            }),
            discussions: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_discussions'
            }),
            followers: new Followers({ns: 'organizations', query: {page_size: 10}}),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Organization'),
                actions: actions
            },
            charts: {
                traffic: {
                    title: this._('Traffic'),
                    default: 'Area',
                    y: [{
                        id: 'nb_uniq_visitors',
                        label: this._('Organization')
                    }, {
                        id: 'datasets_nb_uniq_visitors',
                        label: this._('Datasets')
                    }, {
                        id: 'reuses_nb_uniq_visitors',
                        label: this._('Reuses')
                    }]
                },
                data: {
                    title: this._('Data'),
                    default: 'Bar',
                    y: [{
                        id: 'datasets',
                        label: this._('Datasets')
                    }, {
                        id: 'reuses',
                        label: this._('Reuses')
                    }]
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
        'chart': require('components/charts/widget.vue'),
        'datasets-widget': require('components/dataset/list.vue'),
        'reuses-widget': require('components/reuse/list.vue'),
        'followers-widget': require('components/follow/list.vue'),
        'issues': require('components/issues/list.vue'),
        'discussions': require('components/discussions/list.vue')
    },
    events: {
        'image:saved': function() {
            this.org.fetch();
        }
    },
    methods: {
        setBadges: function() {
            this.$root.$modal(
                {data: {subject: this.org}},
                Vue.extend(require('components/badges/modal.vue'))
            );
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
                this.issues.clear().fetch({org: id});
                this.discussions.clear().fetch({org: id});
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
