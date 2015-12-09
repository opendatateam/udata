<template>
<modal class="modal-primary add-resource-modal" v-ref:modal
    :title="_('Add a resource')">

    <div class="modal-body">
        <resource-form v-ref:form :dataset="dataset"></resource-form>
    </div>

    <footer class="modal-footer text-center">
        <button type="button"
            class="btn btn-primary btn-flat pointer pull-left"
            v-show="$refs.form.resource.filetype"
            @click="save">
            {{ _('Save') }}
        </button>
        <button type="button" class="btn btn-outline btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import Dataset from 'models/dataset';

export default {
    data: function() {
        return {
            dataset: new Dataset()
        };
    },
    components: {
        'modal': require('components/modal.vue'),
        'resource-form': require('components/dataset/resource/form.vue')
    },
    methods: {
        save: function() {
            if (this.$refs.form.validate()) {
                this.dataset.save_resource(this.$refs.form.serialize());
                this.$refs.modal.close();
                return true;
            }
        }
    }
};
</script>
