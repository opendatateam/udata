<template>
<modal :title="_('Confirm deletion')"
    class="modal-danger harvest-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this harvest source') }}
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
</template>

<script>
import API from 'api';
import Modal from 'components/modal.vue';

export default {
    components: {Modal},
    props:  {
        source: Object
    },
    methods: {
        confirm() {
            API.harvest.delete_harvest_source({ident: this.source.id},
                (response) => {
                    this.source.fetch();
                    this.$refs.modal.close();
                },
                this.$root.handleApiError
            );
        }
    }
};
</script>
