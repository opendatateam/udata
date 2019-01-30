<template>
<div>
<modal :title="_('Publish')"
    class="modal-warning post-publish-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to publish this post') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure?') }}
        </p>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-outline pull-left"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
        <button type="button" class="btn btn-outline"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import API from 'api';
import Modal from 'components/modal.vue';

export default {
    components: {Modal},
    props: {
        post: Object,
    },
    methods: {
        confirm() {
            API.posts.publish_post({post: this.post.id}, (response) => {
                this.post.on_fetched(response);
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Post published'),
                });
                this.$refs.modal.close();
                this.$go({name: 'post', params: {oid: this.post.id}});
            }, this.$root.handleApiError);
        }
    }
};
</script>
