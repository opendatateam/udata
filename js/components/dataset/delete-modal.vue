<style lang="less"></style>

<template>
<modal title="{{ _('Confirm deletion') }}"
    modalclass="modal-danger dataset-delete-modal"
    v-ref="modal">

    <div class="modal-body">
        <p class="lead text-center">
            {{ _('You are about to delete this dataset') }}
        </p>
        <p class="lead text-center">
            {{ _('Are you sure?') }}
        </p>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-warning btn-flat pointer pull-left"
            v-on="click: confirm">
            {{ _('Confirm') }}
        </button>
        <button v-show="confirm" type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
'use strict';

module.exports = {
    components: {
        'modal': require('components/modal.vue')
    },
    data: function() {
        return {
            edit: false,
            confirm: false,
            dataset: {},
            // resource: {}
        };
    },
    methods: {
        confirm: function() {
            this.$.modal.close();
        }
    }
};
</script>
