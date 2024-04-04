<template>
<modal :title="_('Confirm deletion')"
    class="modal-danger organization-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this organization') }}
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
</template>

<script>
import API from 'api';
import Modal from 'components/modal.vue';

export default {
    components: {Modal},
    props: {
        organization: Object
    },
    methods: {
        confirm() {
            API.organizations.delete_organization(
                {org: this.organization.id},
                (response) => {
                    this.organization.fetch();
                    this.$refs.modal.close();
                },
                this.$root.handleApiError
            );
        }
    }
};
</script>
