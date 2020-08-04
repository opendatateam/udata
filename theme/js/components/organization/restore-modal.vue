<template>
<div>
<modal :title="_('Confirm restore')"
    class="modal-info organization-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to restore this organization') }}
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
        <button type="button" class="btn btn-warning btn-flat"
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
        organization: Object,
    },
    methods: {
        confirm() {
            const restore_organization = this.organization;
            restore_organization.deleted = null;
            API.organizations.update_organization(
                {org: this.organization.id, payload: restore_organization},
                (response) => {
                    this.organization.on_fetched(response);
                    this.$refs.modal.close();
                },
                this.$root.handleApiError
            );
        }
    }
};
</script>
