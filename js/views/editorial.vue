<template>
    <div class="row">
        <datasets class="col-xs-12 col-md-6"
            :title="_('Featured datasets')"
            :datasets="home_datasets.items">
        </datasets>
        <reuses class="col-xs-12 col-md-6"
            :title="_('Featured reuses')"
            :reuses="home_reuses.items">
        </reuses>
    </div>

    <div class="row">
        <posts class="col-xs-12" :posts="posts"></posts>
    </div>
    <div class="row">
        <topics class="col-xs-12" :topics="topics"></topics>
    </div>
</template>

<script>
import Posts from 'models/posts';
import Topics from 'models/topics';
import {List} from 'models/base';
import API from 'api';

export default {
    name: 'EditorialView',
    data: function() {
        return {
            posts: new Posts({query: {sort: '-created', page_size: 10}}),
            topics: new Topics({query: {sort: '-created', page_size: 10}}),
            home_datasets: new List({ns: 'site', fetch: 'get_home_datasets'}),
            home_reuses: new List({ns: 'site', fetch: 'get_home_reuses'})
        };
    },
    computed: {
        meta: function() {
            return {
                title: 'Editorial'
            };
        }
    },
    components: {
        datasets: require('components/dataset/card-list.vue'),
        reuses: require('components/reuse/card-list.vue'),
        posts: require('components/post/list.vue'),
        topics: require('components/topic/list.vue')
    },
    events: {
        'dataset-card-list:submit': function(order) {
            API.site.set_home_datasets(
                {payload: order},
                this.home_datasets.on_fetched.bind(this.home_datasets)
            );
        },
        'reuse-card-list:submit': function(order) {
            API.site.set_home_reuses(
                {payload: order},
                this.home_reuses.on_fetched.bind(this.home_reuses)
            );
        }
    },
    route: {
        activate() {
            this.$dispatch('meta:updated', this.meta);
        }
    },
    attached: function() {
        this.home_datasets.fetch();
        this.home_reuses.fetch();
        this.posts.fetch();
        this.topics.fetch();
    }
};
</script>
