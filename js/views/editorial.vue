<template>
<layout :title="_('Editorial')">
    <div class="row">
        <dataset-cards class="col-xs-12 col-md-6"
            :title="_('Featured datasets')"
            :datasets="home_datasets.items">
        </dataset-cards>
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
</layout>
</template>

<script>
import Posts from 'models/posts';
import Topics from 'models/topics';
import {List} from 'models/base';
import API from 'api';
import Layout from 'components/layout.vue';
import DatasetCards from 'components/dataset/card-list.vue';



export default {
    name: 'EditorialView',
    data: function() {
        return {
            posts: new Posts({query: {sort: '-created', page_size: 10}}),
            topics: new Topics({query: {sort: '-created', page_size: 10}}),
            home_datasets: new List({ns: 'site', fetch: 'get_home_datasets', mask: DatasetCards.MASK}),
            home_reuses: new List({ns: 'site', fetch: 'get_home_reuses'})
        };
    },
    components: {
        reuses: require('components/reuse/card-list.vue'),
        posts: require('components/post/list.vue'),
        topics: require('components/topic/list.vue'),
        DatasetCards,
        Layout
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
    attached: function() {
        this.home_datasets.fetch();
        this.home_reuses.fetch();
        this.posts.fetch();
        this.topics.fetch();
    }
};
</script>
