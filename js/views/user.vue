<template>
    <div class="row">
        <profile :user="user" class="col-xs-12 col-md-6"></profile>
        <chart title="Traffic" :metrics="metrics" class="col-xs-12 col-md-6"
            x="date" :y="y"></chart>
    </div>

    <div class="row">
        <datasets class="col-xs-12" :datasets="datasets"></datasets>
    </div>

    <div class="row">
        <reuses class="col-xs-12" :reuses="reuses"></reuses>
    </div>

    <div class="row">
        <communities class="col-xs-12" :communities="communities"></communities>
    </div>

    <div class="row">
        <harvesters id="harvesters-widget" class="col-xs-12" :owner="user"></harvesters>
    </div>
</template>

<script>
import moment from 'moment';
import User from 'models/user';
import Reuses from 'models/reuses';
import Datasets from 'models/datasets';
import Metrics from 'models/metrics';
import CommunityResources from 'models/communityresources';

export default {
    name: 'user-view',
    data: function() {
        return {
            user: new User(),
            metrics: new Metrics({
                query: {
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                }
            }),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}}),
            datasets: new Datasets({query: {sort: '-created', page_size: 10}}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            meta: {
                title: null,
                subtitle: this._('User')
            },
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
        datasets: require('components/dataset/list.vue'),
        reuses: require('components/reuse/list.vue'),
        harvesters: require('components/harvest/sources.vue'),
        communities: require('components/communityresource/list.vue')
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
        },
        'user.fullname': function(fullname) {
            if (fullname) {
                this.meta.title = fullname;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        },
        data() {
            this.user.fetch(this.$route.params.oid);
        }
    }
};
</script>
