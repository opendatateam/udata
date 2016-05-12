<template>
<layout :title="reuse.title || ''" :subtitle="_('Reuse')"
    :actions="actions" :badges="badges" :page="reuse.page || ''">
    <div class="row">
        <sbox class="col-lg-4 col-xs-6" v-for="b in boxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </sbox>
    </div>
    <div class="row">
        <reuse-details :reuse="reuse" class="col-xs-12 col-md-6"></reuse-details>
        <dataset-cards id="datasets-list" :datasets="reuse.datasets"
            class="col-xs-12 col-md-6">
        </dataset-cards>
    </div>

    <div class="row">
        <chart id="traffic" title="Traffic" :metrics="metrics" class="col-xs-12"
            x="date" :y="y"></chart>
    </div>

    <div class="row">
        <issue-list id="issues-widget" class="col-xs-12 col-md-6" :issues="issues"></issue-list>
        <discussions id="discussions-widget" class="col-xs-12 col-md-6" :discussions="discussions"></discussions>
    </div>

    <div class="row">
        <followers id="followers-widget" class="col-xs-12" :followers="followers"></followers>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import Reuse from 'models/reuse';
import Followers from 'models/followers';
import Metrics from 'models/metrics';
import Vue from 'vue';
import Issues from 'models/issues';
import Discussions from 'models/discussions';
import mask from 'models/mask';
// Widgets
import DatasetCards from 'components/dataset/card-list.vue';
import DiscussionList from 'components/discussions/list.vue';
import IssueList from 'components/issues/list.vue';
import Layout from 'components/layout.vue';

const MASK = `datasets{${mask(DatasetCards.MASK)}},*`;

export default {
    name: 'ReuseView',
    data() {
        const actions = [{
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
            reuse: new Reuse({mask: MASK}),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            followers: new Followers({ns: 'reuses', query: {page_size: 10}}),
            issues: new Issues({query: {sort: '-created', page_size: 10}, mask: IssueList.MASK}),
            discussions: new Discussions({query: {sort: '-created', page_size: 10}, mask: DiscussionList.MASK}),
            actions: actions,
            badges: [],
            y: [{
                id: 'views',
                label: this._('Views')
            }, {
                id: 'followers',
                label: this._('Followers')
            }]
        };
    },
    computed: {
        boxes() {
            if (!this.reuse.metrics) {
                return [];
            }
            return [{
                value: this.reuse.metrics.datasets || 0,
                label: this.reuse.metrics.datasets ? this._('Datasets') : this._('Dataset'),
                icon: 'retweet',
                color: 'green',
                target: '#datasets-list'
            }, {
                value: this.reuse.metrics.followers || 0,
                label: this.reuse.metrics.followers ? this._('Followers') : this._('Follower'),
                icon: 'users',
                color: 'yellow',
                target: '#followers-widget'
            }, {
                value: this.reuse.metrics.views || 0,
                label: this._('Views'),
                icon: 'eye',
                color: 'purple',
                target: '#traffic'
            }];
        }
    },
    components: {
        sbox: require('components/containers/small-box.vue'),
        chart: require('components/charts/widget.vue'),
        'reuse-details': require('components/reuse/details.vue'),
        followers: require('components/follow/list.vue'),
        DiscussionList,
        IssueList,
        DatasetCards,
        Layout
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.reuse.datasets = ids;
            this.reuse.save();
        }
    },
    methods: {
        edit() {
            this.$go({name: 'reuse-edit', params: {oid: this.reuse.id}});
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/reuse/delete-modal.vue'),
                {reuse: this.reuse}
            );
        },
        transfer_request() {
            this.$root.$modal(
                require('components/transfer/request-modal.vue'),
                {subject: this.reuse}
            );
        },
        setBadges() {
            this.$root.$modal(
                require('components/badges/modal.vue'),
                {subject: this.reuse}
            );
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.reuse.id) {
                this.reuse.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    },
    watch: {
        'reuse.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.followers.fetch({id: id});
                this.issues.fetch({'for': id});
                this.discussions.fetch({'for': id});
            }
        },
        'reuse.deleted': function(deleted) {
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
