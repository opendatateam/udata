<template>
<layout :title="org.name || ''" :subtitle="_('Organization')"
    :actions="actions" :badges="badges" :page="org.page || ''">
    <div class="row">
        <sbox class="col-lg-3 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </sbox>
    </div>
    <div class="row">
        <profile :org="org" class="col-xs-12 col-md-6"></profile>
        <members :org="org" class="col-xs-12 col-md-6"></members>
    </div>

    <div class="row">
        <chart id="trafic-widget" class="col-xs-12"
            :title="charts.traffic.title" :default="charts.traffic.default"
            :metrics="metrics"
            x="date" :y="charts.traffic.y"
            >
        </chart>
    </div>

    <div class="row">
        <dataset-list id="datasets-widget" class="col-xs-12" :datasets="datasets"
            :downloads="downloads">
        </dataset-list>
    </div>

    <div class="row">
        <reuse-list id="reuses-widget" class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>

    <div class="row">
        <issue-list id="issues-widget" class="col-xs-12 col-md-6" :issues="issues"></issue-list>
        <discussion-list id="discussions-widget" class="col-xs-12 col-md-6" :discussions="discussions"></discussion-list>
    </div>

    <div class="row">
        <followers id="followers-widget" class="col-xs-12 col-md-6" :followers="followers"></followers>
        <harvesters id="harvesters-widget" class="col-xs-12 col-md-6" :owner="org"></harvesters>
    </div>

    <div class="row">
        <communities class="col-xs-12" :communities="communities"></communities>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import Vue from 'vue';
import URLs from 'urls';
import Followers from 'models/followers';
import Metrics from 'models/metrics';
import Organization from 'models/organization';
import CommunityResources from 'models/communityresources';
import {PageList} from 'models/base';
// Widgets
import DatasetList from 'components/dataset/list.vue';
import DiscussionList from 'components/discussions/list.vue';
import IssueList from 'components/issues/list.vue';
import Layout from 'components/layout.vue';
import ReuseList from 'components/reuse/list.vue';

export default {
    name: 'OrganizationView',
    data() {
        let actions = [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
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
            org: new Organization(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            reuses: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_reuses',
                search: 'title',
                mask: ReuseList.MASK
            }),
            datasets: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_datasets',
                search: 'title',
                mask: DatasetList.MASK
            }),
            issues: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_issues',
                mask: IssueList.MASK
            }),
            discussions: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_discussions',
                mask: DiscussionList.MASK
            }),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            followers: new Followers({ns: 'organizations', query: {page_size: 10}}),
            actions: actions,
            badges: [],
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
        boxes() {
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
        downloads() {
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
        sbox: require('components/containers/small-box.vue'),
        profile: require('components/organization/profile.vue'),
        members: require('components/organization/members.vue'),
        chart: require('components/charts/widget.vue'),
        followers: require('components/follow/list.vue'),
        harvesters: require('components/harvest/sources.vue'),
        communities: require('components/dataset/communityresource/list.vue'),
        DiscussionList,
        DatasetList,
        ReuseList,
        IssueList,
        Layout,
    },
    events: {
        'image:saved': function() {
            this.org.fetch();
        }
    },
    methods: {
        edit() {
            this.$go({name: 'organization-edit', params: {oid: this.org.id}});
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/organization/delete-modal.vue'),
                {organization: this.org}
            );
        },
        setBadges() {
            this.$root.$modal(
                require('components/badges/modal.vue'),
                {subject: this.org}
            );
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.org.id) {
                this.org.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    },
    watch: {
        'org.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({org: id});
                this.datasets.clear().fetch({org: id});
                this.issues.clear().fetch({org: id});
                this.discussions.clear().fetch({org: id});
                this.followers.fetch({id: id});
                this.communities.clear().fetch({organization: id});
            } else {
                this.datasets.clear();
                this.reuses.clear();
                this.followers.clear();
                this.communities.clear();
            }
        },
        'org.deleted': function(deleted) {
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
