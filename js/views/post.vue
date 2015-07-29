<template>
    <div class="row">
        <post-content post="{{post}}" class="col-md-12"></post-details>
    </div>
    <div class="row">
        <datasets-list datasets="{{post.datasets}}" class="col-md-6"></datasets-list>
        <reuses-list reuses="{{post.reuses}}" class="col-md-6"></reuses-list>
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    Post = require('models/post');

module.exports = {
    name: 'PostView',
    data: function() {
        return {
            post_id: null,
            post: new Post(),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Post')
            }
        };
    },
    components: {
        'small-box': require('components/containers/small-box.vue'),
        'post-content': require('components/post/content.vue'),
        'datasets-list': require('components/dataset/card-list.vue'),
        'reuses-list': require('components/reuse/card-list.vue')
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.post.datasets = ids;
            this.post.save();
        },
        'reuse-card-list:submit': function(ids) {
            this.post.reuses = ids;
            this.post.save();
        }
    },
    watch: {
        post_id: function(id) {
            if (id) {
                this.post.fetch(id);
            }
        },
        'post.page': function(page) {
            if (page) {
                this.meta.page = page;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'post.name': function(name) {
            if (name) {
                this.meta.title = name;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    }
};
</script>
