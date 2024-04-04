<template>
<div>
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
        <dataset-list id="datasets-widget" class="col-xs-12" :datasets="datasets"
            :downloads="downloads">
        </dataset-list>
    </div>

    <div class="row">
        <reuse-list id="reuses-widget" class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>

    <div class="row">
        <discussion-list id="discussions-widget" class="col-xs-12" :discussions="discussions"></discussion-list>
    </div>

    <div class="row">
        <followers id="followers-widget" class="col-xs-12 col-md-6" :followers="followers"></followers>
        <harvesters id="harvesters-widget" class="col-xs-12 col-md-6" :owner="org"></harvesters>
    </div>

    <div class="row">
        <communities class="col-xs-12" :communities="communities"></communities>
    </div>
</layout>
</div>
</template>

<script>
import moment from 'moment';
import Vue from 'vue';
import URLs from 'urls';
import Organization from 'models/organization';
import CommunityResources from 'models/communityresources';
import {PageList, ModelPage} from 'models/base';
// Widgets
import DatasetList from 'components/dataset/list.vue';
import DiscussionList from 'components/discussions/list.vue';
import Layout from 'components/layout.vue';
import ReuseList from 'components/reuse/list.vue';

export default {
    name: 'OrganizationView',
    data() {
        return {
            org: new Organization(),
            reuses: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_reuses',
                search: 'title',
                mask: ReuseList.MASK.concat(['deleted'])
            }),
            datasets: new ModelPage({
                query: {page_size: 10, sort: '-created'},
                ns: 'organizations',
                fetch: 'list_organization_datasets',
                search: 'title',
                mask: DatasetList.MASK.concat(['deleted'])
            }),
            discussions: new PageList({
                ns: 'organizations',
                fetch: 'list_organization_discussions',
                mask: DiscussionList.MASK
            }),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            followers: new ModelPage({
                query: {page_size: 10},
                ns: 'organizations',
                fetch: 'list_organization_followers'
            }),
            badges: [],
            charts: {
                traffic: {
                    title: this._('Traffic'),
                    default: 'Area',
                    y: [{
                        id: 'views',
                        label: this._('Organization')
                    }, {
                        id: 'datasets_views',
                        label: this._('Datasets')
                    }, {
                        id: 'reuses_views',
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
        actions() {
            const actions = []

            if (this.org.is_admin(this.$root.me)) {
                actions.push({
                    label: this._('Edit this organization'),
                    icon: 'edit',
                    method: this.edit
                });

                if(!this.org.deleted) {
                    actions.push({
                        label: this._('Delete'),
                        icon: 'trash',
                        method: this.confirm_delete
                    });
                } else {
                    actions.push({
                        label: this._('Restore'),
                        icon: 'undo',
                        method: this.confirm_restore
                    });
                }
            }

            if (this.$root.me.is_admin) {
                actions.push({divider: true});
                actions.push({
                    label: this._('Badges'),
                    icon: 'bookmark',
                    method: this.setBadges
                });
            }
            return actions;
        },
        boxes() {
            if (!this.org.metrics) {
                return [];
            }
            return [{
                value: this.org.metrics.datasets || 0,
                label: this.org.metrics.datasets ? this._('Public datasets') : this._('Public dataset'),
                icon: 'cubes',
                color: 'aqua',
                target: '#datasets-widget'
            }, {
                value: this.org.metrics.reuses || 0,
                label: this.org.metrics.reuses ? this._('Public reuses') : this._('Public reuse'),
                icon: 'recycle',
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
        confirm_restore() {
            this.$root.$modal(
                require('components/organization/restore-modal.vue'),
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
                this.reuses.clear().fetch({org: id});
                this.datasets.clear().fetch({org: id});
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
            } else {
                this.badges = [];
            }
        }
    }
};
</script>
