<template>
<layout :title="_('Editorial')">
    <div class="row">
        <dataset-card-list class="col-xs-12 col-md-6"
            :title="_('Featured datasets')"
            :datasets="home_datasets.items"
            :loading="home_datasets.loading">
        </dataset-card-list>
        <reuse-card-list class="col-xs-12 col-md-6"
            :title="_('Featured reuses')"
            :reuses="home_reuses.items"
            :loading="home_reuses.loading">
        </reuse-card-list>
    </div>

    <div class="row">
        <post-list class="col-xs-12" :posts="posts"></post-list>
    </div>
    <div class="row">
        <topic-list class="col-xs-12" :topics="topics"></topic-list>
    </div>
</layout>
</template>

<script>
import Posts from 'models/posts';
import Topics from 'models/topics';
import Reuse from 'models/reuse';
import Dataset from 'models/dataset';
import {List} from 'models/base';
import API from 'api';
import Layout from 'components/layout.vue';
import DatasetCardList from 'components/dataset/card-list.vue';
import ReuseCardList from 'components/reuse/card-list.vue';
import TopicList from 'components/topic/list.vue';
import PostList from 'components/post/list.vue';


export default {
    name: 'editorial-view',
    data() {
        return {
            posts: new Posts({query: {sort: '-created', page_size: 10}, mask: PostList.MASK}),
            topics: new Topics({query: {sort: '-created', page_size: 10}, mask: TopicList.MASK}),
            home_datasets: new List({ns: 'site', fetch: 'get_home_datasets',
                                     mask: DatasetCardList.MASK, model: Dataset}),
            home_reuses: new List({ns: 'site', fetch: 'get_home_reuses',
                                   mask: ReuseCardList.MASK, model: Reuse})
        };
    },
    components: {
        PostList,
        TopicList,
        DatasetCardList,
        ReuseCardList,
        Layout
    },
    events: {
        'dataset-card-list:submit': function(order) {
            API.site.set_home_datasets(
                {payload: order},
                this.home_datasets.on_fetched.bind(this.home_datasets),
                this.$root.handleApiError
            );
        },
        'reuse-card-list:submit': function(order) {
            API.site.set_home_reuses(
                {payload: order},
                this.home_reuses.on_fetched.bind(this.home_reuses),
                this.$root.handleApiError
            );
        }
    },
    attached() {
        this.home_datasets.fetch();
        this.home_reuses.fetch();
        this.posts.fetch();
        this.topics.fetch();
    }
};
</script>
