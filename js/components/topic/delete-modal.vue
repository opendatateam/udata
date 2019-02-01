<template>
<div>
<modal :title="_('Confirm deletion')"
    class="modal-danger topic-delete-modal"
    v-ref:modal>

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this topic') }}
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
        topic: Object,
    },
    methods: {
        confirm() {
            API.topics.delete_topic({topic: this.topic.id},
                (response) => {
                    this.$dispatch('notify', {
                        autoclose: true,
                        title: this._('Topic deleted'),
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
