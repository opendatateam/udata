<template>
    <div class="row">
        <datasets-list class="col-md-6"
            title="{{ _('Featured datasets') }}"
            datasets="{{home_datasets.items}}">
        </datasets-list>
        <reuses-list class="col-md-6"
            title="{{ _('Featured reuses') }}"
            reuses="{{home_reuses.items}}">
        </reuses-list>
    </div>

    <div class="row">
        <posts-widget id="posts-widget" class="col-md-12" posts="{{posts}}"></posts-widget>
    </div>
    <div class="row">
        <topics-widget id="topics-widget" class="col-md-12" topics="{{topics}}"></topics-widget>
    </div>
</template>

<script>
'use strict';

var Posts = require('models/posts'),
    Topics = require('models/topics'),
    List = require('models/base_list'),
    API = require('api');

module.exports = {
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
        'datasets-list': require('components/dataset/card-list.vue'),
        'reuses-list': require('components/reuse/card-list.vue'),
        'posts-widget': require('components/post/list.vue'),
        'topics-widget': require('components/topic/list.vue')
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
