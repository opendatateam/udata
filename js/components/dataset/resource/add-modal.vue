<style lang="less"></style>

<template>
<modal class="modal-primary add-resource-modal"
    title="{{ _('Add a resource') }}">

    <div class="modal-body">
        <resource-form v-ref="form" dataset="{{dataset}}"></resource-form>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-primary btn-flat pointer pull-left"
            data-dismiss="modal"
            v-show="$.form.resource.type">
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
'use strict';

module.exports = {
    data: function() {
        return {
            dataset: {}
        };
    },
    components: {
        'modal': require('components/modal.vue'),
        'resource-form': require('components/dataset/resource/form.vue')
    },
    methods: {
        save: function() {
            if (this.$.form.validate()) {
                this.dataset.save_resource(this.$.form.serialize());
                this.$.modal.close();
                return true;
            }
        }
    }
};
</script>
