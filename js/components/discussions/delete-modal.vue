<template>
<modal v-ref:modal :title="_('Confirm deletion')"
    class="modal-danger discussion-delete-modal">

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this discussion') }}
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
        <button v-show="cancel" type="button" class="btn btn-danger btn-flat pointer"
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
            cancel: true,
            discussionid: null
        };
    },
    methods: {
        confirm: function() {
            API.discussions.delete_discussion({id: this.discussionid},
                (response) => {
                    this.$refs.modal.close();
                }
            );
        }
    }
};
</script>
