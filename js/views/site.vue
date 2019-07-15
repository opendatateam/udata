<template>
<div>
<layout :title="_('Site')">
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </small-box>
    </div>
    <div class="row">
        <chart-widget title="Traffic" :metrics="metrics" class="col-xs-12"
            x="date" :y="y"></chart-widget>
    </div>

    <div class="row">
        <dataset-list id="datasets" class="col-xs-12" :datasets="datasets"></dataset-list>
    </div>
    <div class="row">
        <reuse-list id="reuses" class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>
    <div class="row">
        <org-list id="organizations" class="col-xs-12" :organizations="organizations"></org-list>
    </div>
    <div class="row">
        <user-list id="users" class="col-xs-12" :users="users"></user-list>
    </div>
    <div class="row">
        <issue-list class="col-xs-12 col-md-6" :issues="issues"></issue-list>
        <discussion-list class="col-xs-12 col-md-6" :discussions="discussions"></discussion-list>
    </div>
    <div class="row">
        <community-list class="col-xs-12" :communities="communities"></community-list>
    </div>
</layout>
</div>
</template>

<script>
import moment from 'moment';

import Reuses from 'models/reuses';
import Datasets from 'models/datasets';
import Metrics from 'models/metrics';
import Issues from 'models/issues';
import Discussions from 'models/discussions';
import Users from 'models/users';
import Organizations from 'models/organizations';
import CommunityResources from 'models/communityresources';
// Widgets
import SmallBox from 'components/containers/small-box.vue';
import Layout from 'components/layout.vue';
import DatasetList from 'components/dataset/list.vue';
import ReuseList from 'components/reuse/list.vue';
import OrgList from 'components/organization/list.vue';
import IssueList from 'components/issues/list.vue';
import DiscussionList from 'components/discussions/list.vue';
import CommunityList from 'components/dataset/communityresource/list.vue';
import ChartWidget from 'components/charts/widget.vue';
import UserList from 'components/user/list.vue';

export default {
    name: 'SiteView',
    data() {
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
            reuses: new Reuses({query: {sort: '-created', page_size: 10}, mask: ReuseList.MASK}),
            datasets: new Datasets({query: {sort: '-created', page_size: 10}, mask: DatasetList.MASK}),
            organizations: new Organizations({query: {sort: '-created', page_size: 10}, mask: OrgList.MASK}),
            users: new Users({query: {sort: '-created', page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}, mask: IssueList.MASK}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}, mask:DiscussionList.MASK}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}, mask: CommunityList.MASK}),
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
        boxes() {
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
                icon: 'recycle',
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
        ChartWidget,
        CommunityList,
        DatasetList,
        DiscussionList,
        IssueList,
        Layout,
        OrgList,
        ReuseList,
        SmallBox,
        UserList,
    },
    methods: {
        fetch_metrics() {
            if (this.$root.site.id) {
                this.metrics.fetch({id: this.$root.site.id});
            }
        }
    },
    attached() {
        this.fetch_metrics();
        this.datasets.fetch();
        this.reuses.fetch();
        this.users.fetch();
        this.issues.fetch();
        this.discussions.fetch();
        this.organizations.fetch();
        this.communities.fetch();
    },
    watch: {
        '$root.site.id': function() {
            this.fetch_metrics();
        }
    }
};
</script>
