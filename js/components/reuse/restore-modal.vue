<template>
<modal :title="_('Confirm restore')"
    class="modal-info reuse-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to restore this reuse') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure?') }}
        </p>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-success btn-flat pull-left"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import Modal from 'components/modal.vue';

export default {
    components: {Modal},
    props: {
        reuse: Object
    },
    methods: {
        confirm() {
            const restore_reuse = this.reuse;
            restore_reuse.deleted = null;
            API.reuses.update_reuse({reuse: this.reuse.id, payload: restore_reuse},
                (response) => {
                    this.reuse.on_fetched(response);
                    this.$refs.modal.close();
                }
            );
        }
    }
};
</script>
