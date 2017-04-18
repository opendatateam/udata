<template>
<modal class="modal-primary add-resource-modal" v-ref:modal
    :title="_('Add a resource')">

    <div class="modal-body">
        <resource-form v-ref:form :dataset="dataset"></resource-form>
    </div>

    <footer class="modal-footer text-center">
        <button type="button"
            class="btn btn-primary btn-flat pull-left"
            v-show="$refs.form.resource.filetype"
            @click="save">
            {{ _('Save') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import Dataset from 'models/dataset';
import Modal from 'components/modal.vue';
import ResourceForm from 'components/dataset/resource/form.vue';

export default {
    props: {
        dataset: {
            type: Dataset,
            required: true,
        }
    },
    components: {Modal, ResourceForm},
    methods: {
        save() {
            if (this.$refs.form.validate()) {
                this.dataset.save_resource(this.$refs.form.serialize());
                this.$refs.modal.close();
                return true;
            }
        }
    }
};
</script>
