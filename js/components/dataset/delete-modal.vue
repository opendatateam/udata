<template>
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
        <button type="button" class="btn btn-warning btn-flat pointer pull-left"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';

export default {
    components: {
        modal: require('components/modal.vue')
    },
    data: function() {
        return {
            dataset: {}
        };
    },
    methods: {
        confirm: function() {
            API.datasets.delete_dataset({dataset: this.dataset.id},
                (response) => {
                    this.dataset.fetch();
                    this.$refs.modal.close();
                }
            );
        }
    }
};
</script>
