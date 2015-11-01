<template>
    <div class="row">
        <post-content :post="post" class="col-xs-12"></post-content>
    </div>
    <div class="row">
        <datasets :datasets="post.datasets" class="col-xs-12 col-md-6"></datasets>
        <reuses :reuses="post.reuses" class="col-xs-12 col-md-6"></reuses>
    </div>
</template>

<script>
import moment from 'moment';
import Post from 'models/post';

export default {
    name: 'PostView',
    data: function() {
        return {
            post: new Post(),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Post')
            }
        };
    },
    components: {
        'post-content': require('components/post/content.vue'),
        datasets: require('components/dataset/card-list.vue'),
        reuses: require('components/reuse/card-list.vue')
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
        activate() {
            this.$dispatch('meta:updated', this.meta);
        },
        data() {
            this.post.fetch(this.$route.params.oid);
        }
    },
    watch: {
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
