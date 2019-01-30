<template>
<div>
<modal :title="_('Confirm deletion')"
    class="modal-danger post-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this post') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure?') }}
        </p>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-warning btn-flat pull-left"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
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
            API.posts.delete_post({post: this.post.id},
                (response) => {
                    this.$dispatch('notify', {
                        autoclose: true,
                        title: this._('Post deleted'),
                    });
                    this.$refs.modal.close();
                    this.$go({name: 'editorial'});
                },
                this.$root.handleApiError
            );
        }
    }
};
</script>
