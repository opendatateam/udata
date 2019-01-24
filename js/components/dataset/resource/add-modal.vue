<template>
<div>
<modal class="modal-primary add-resource-modal" v-ref:modal
    :title="_('Add a resource')" :large="editing">

    <div class="modal-body">
        <resource-form v-ref:form :dataset="dataset" is-upload></resource-form>
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
import WatchRefs from 'mixins/watch-refs';

export default {
    name: 'add-resource-modal',
    mixins: [WatchRefs],
    props: {
        dataset: {
            type: Dataset,
            required: true,
        }
    },
    components: {Modal, ResourceForm},
    data() {
        return {editing: false};
    },
    methods: {
        upload() {
            this.$refs.form.isUpload = true;
        },
        save() {
            if (this.$refs.form.validate()) {
                this.dataset.save_resource(this.$refs.form.serialize());
                this.$refs.modal.close();
                return true;
            }
        },
    },
    watchRefs: {
        'form.hasData': function(hasData) {
            this.editing = hasData;
        },
    },
};
</script>
