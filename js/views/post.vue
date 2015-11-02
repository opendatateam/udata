<template>
<layout :title="post.name || ''" :subtitle="_('Post')" :page="post.page || ''">
    <div class="row">
        <post-content :post="post" class="col-xs-12"></post-content>
    </div>
    <div class="row">
        <datasets :datasets="post.datasets" class="col-xs-12 col-md-6"></datasets>
        <reuses :reuses="post.reuses" class="col-xs-12 col-md-6"></reuses>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import Post from 'models/post';
import Layout from 'components/layout.vue';

export default {
    name: 'PostView',
    data: function() {
        return {
            post: new Post()
        };
    },
    components: {
        'post-content': require('components/post/content.vue'),
        datasets: require('components/dataset/card-list.vue'),
        reuses: require('components/reuse/card-list.vue'),
        Layout
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.post.datasets = ids;
            this.post.save();
            return true;
        },
        'reuse-card-list:submit': function(ids) {
            this.post.reuses = ids;
            this.post.save();
            return true;
        }
    },
    route: {
        data() {
            this.post.fetch(this.$route.params.oid);
        }
    }
};
</script>
