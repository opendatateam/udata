<template>
<div>
<modal class="modal-primary add-resource-modal" v-ref:modal
    :title="_('Add a resource')" :large="editing">

    <div class="modal-body">
        <resource-form v-ref:form :dataset="dataset"></resource-form>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-sm btn-primary btn-flat pull-left"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
        <button type="button"
            class="btn btn-outline btn-flat"
            v-show="editing"
            @click="save">
            {{ _('Save') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import Dataset from 'models/dataset';
import Modal from 'components/modal.vue';
import ResourceForm from 'components/dataset/resource/form.vue';

export default {
    name: 'add-resource-modal',
    props: {
        dataset: {
            type: Dataset,
            required: true,
        }
    },
    components: {Modal, ResourceForm},
    data() {
        return {ready: false};
    },
    computed: {
        editing() {
            return this.ready && this.$refs && this.$refs.form && this.$refs.form.hasData;
        }
    },
    ready() {
        this.ready = true; // Artificially force editing update because $refs is not reactive
    },
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
