<template>
<layout :title="user.fullname || ''" :subtitle="_('User')" :page="user.page || ''" :actions="actions">
    <div class="row">
        <profile :user="user" class="col-xs-12 col-md-6"></profile>
        <chart title="Traffic" :metrics="metrics" class="col-xs-12 col-md-6"
            x="date" :y="y"></chart>
    </div>

    <div class="row">
        <dataset-list class="col-xs-12" :datasets="datasets"></dataset-list>
    </div>

    <div class="row">
        <reuse-list class="col-xs-12" :reuses="reuses"></reuse-list>
    </div>

    <div class="row">
        <community-list class="col-xs-12" :communities="communities"></community-list>
    </div>

    <div class="row">
        <harvesters id="harvesters-widget" class="col-xs-12" :owner="user"></harvesters>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import User from 'models/user';
import Reuses from 'models/reuses';
import Datasets from 'models/datasets';
import Metrics from 'models/metrics';
import CommunityResources from 'models/communityresources';
import Layout from 'components/layout.vue';
import DatasetList from 'components/dataset/list.vue';
import ReuseList from 'components/reuse/list.vue';
import CommunityList from 'components/dataset/communityresource/list.vue';

export default {
    name: 'user-view',
    data: function() {
        return {
            actions: [
                {
                    label: this._('Edit'),
                    icon: 'edit',
                    method: this.edit
                },
                {
                    label: this._('Delete'),
                    icon: 'trash',
                    method: this.confirm_delete,
                }
            ],
            user: new User(),
            metrics: new Metrics({
                query: {
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                }
            }),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}, mask: ReuseList.MASK}),
            datasets: new Datasets({query: {sort: '-created', page_size: 10}, mask: DatasetList.MASK}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            y: [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'reuses',
                label: this._('Reuses')
            }]
        };
    },
    components: {
        profile: require('components/user/profile.vue'),
        chart: require('components/charts/widget.vue'),
        harvesters: require('components/harvest/sources.vue'),
        CommunityList,
        DatasetList,
        ReuseList,
        Layout
    },
    watch: {
        'user.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({owner: id});
                this.datasets.clear().fetch({owner: id});
                this.communities.clear().fetch({owner: id});
            } else {
                this.datasets.clear();
                this.reuses.clear();
                this.communities.clear();
            }
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.user.id) {
                this.user.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    },
    methods: {
        edit() {
            this.$go('/user/edit/' + this.user.id + '/');
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/user/delete-user-modal.vue'),
                {user: this.user},
            );
        }
    }
};
</script>
