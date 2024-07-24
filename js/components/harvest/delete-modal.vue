<template>
<modal :title="_('Confirm deletion')"
    class="modal-danger harvest-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this harvest source') }}
        </p>
        <div class="lead text-center" v-if="harvestValidationContactForm">
            <p>
                {{ _('Before deleting this harvest source, please contact us through the following contact form to make sure you are not losing any information irrevocably') }}
            </p>
            <a class="btn btn-default btn-flat" href="{{ harvestValidationContactForm }}">
                {{ _('Contact us through the harvest contact form') }}
            </a>
        </div>
        <p class="lead text-center">
            {{ _('Proceed anyway?') }}
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
</template>

<script>
import API from 'api';
import config from 'config';
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
    },
    data() {
        return {
            harvestValidationContactForm: config.harvest_validation_contact_form
        }
    }
};
</script>
