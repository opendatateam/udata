<template>
<modal :title="_('Confirm deletion')"
    class="modal-danger"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete the profile of the user {fullname}.',
                 {fullname: user.fullname}) }}
        </p>
        <p class="lead text-center">
            {{ _('It will not be possible to recover this profile once deleted.') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure ?') }}
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
        user: Object,
    },
    methods: {
        confirm() {
            API.users.delete_user(
                {user: this.user.id},
                response => {
                    this.$refs.modal.close();
                    this.$dispatch('notify', {
                        icon: 'exclamation-triangle',
                        title: this._('The user {fullname} has been successfully deleted',
                                      {fullname: this.user.fullname}
                                     )
                        }
                    );
                    this.$go({name: 'site'});
                },
                response => {
                    this.$refs.modal.close();
                    this.$dispatch('notify', {
                        type: 'error',
                        icon: 'exclamation-triangle',
                        title: this._('An error {status} occured',
                                      {status: response.status}),
                        details: JSON.parse(response.data).message,
                    });
                }
            );
        }
    }
};
</script>
