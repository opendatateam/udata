<template>
<div>
<layout :title="post.name || ''" :subtitle="_('Post')" :page="post.page || ''" :actions="actions">
    <div class="row">
        <post-content :post="post" class="col-xs-12"></post-content>
    </div>
    <div class="row">
        <dataset-card-list editable :datasets="post.datasets" class="col-xs-12 col-md-6"></dataset-card-list>
        <reuse-card-list editable :reuses="post.reuses" class="col-xs-12 col-md-6"></reuse-card-list>
    </div>
</layout>
</div>
</template>

<script>
import moment from 'moment';
import Post from 'models/post';
import Layout from 'components/layout.vue';

import PostContent from 'components/post/content.vue';
import DeleteModal from 'components/post/delete-modal.vue';
import PublishModal from 'components/post/publish-modal.vue';
import UnpublishModal from 'components/post/unpublish-modal.vue';
import DatasetCardList from 'components/dataset/card-list.vue';
import ReuseCardList from 'components/reuse/card-list.vue';

export default {
    name: 'PostView',
    MASK: [
        '*',
        `datasets{${DatasetCardList.MASK.join(',')}}`,
        `reuses{${ReuseCardList.MASK.join(',')}}`,
    ],
    data() {
        return {
            post: new Post(),
        };
    },
    computed: {
        actions() {
            return [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
            },
            this.post.published ? {
                label: this._('Unpublish'),
                icon: 'eye-slash',
                method: this.unpublish,
            } : {
                label: this._('Publish'),
                icon: 'eye',
                method: this.publish,
            },
            {divider: true},
            {
                label: this._('Delete'),
                icon: 'trash',
                method: this.confirm_delete
            }];
        }
    },
    components: {Layout, PostContent, DatasetCardList, ReuseCardList},
    events: {
        'dataset-card-list:submit': function(ids) {
            this.post.datasets = ids.map(id => ({id, class: 'Dataset'}));
            this.post.save();
            return true;
        },
        'reuse-card-list:submit': function(ids) {
            this.post.reuses = ids.map(id => ({id, class: 'Reuse'}));
            this.post.save();
            return true;
        }
    },
    methods: {
        edit() {
            this.$go({name: 'post-edit', params: {oid: this.post.id}});
        },
        confirm_delete() {
            this.$root.$modal(DeleteModal, {post: this.post});
        },
        publish() {
            this.$root.$modal(PublishModal, {post: this.post});
        },
        unpublish() {
            this.$root.$modal(UnpublishModal, {post: this.post});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.post.id) {
                this.post.fetch(this.$route.params.oid, this.$options.MASK);
                this.$scrollTo(this.$el);
            }
        }
    }
};
</script>
