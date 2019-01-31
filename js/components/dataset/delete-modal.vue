<template>
<div>
<modal :title="_('Confirm deletion')"
    class="modal-danger dataset-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this dataset') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure?') }}
        </p>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-danger btn-flat pull-left"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat"
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
        dataset: Object,
    },
    methods: {
        confirm() {
            API.datasets.delete_dataset({dataset: this.dataset.id},
                (response) => {
                    this.dataset.fetch();
                    this.$refs.modal.close();
                },
                this.$root.handleApiError
            );
        }
    }
};
</script>
