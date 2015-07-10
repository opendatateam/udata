<style lang="less"></style>

<template>
<w-modal title="{{ _('Confirm deletion') }}"
    modalclass="modal-danger discussion-delete-modal"
    v-ref="modal">

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
            v-on="click: confirm">
            {{ _('Confirm') }}
        </button>
        <button v-show="cancel" type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</w-modal>
</template>

<script>
'use strict';

var API = require('api');

module.exports = {
    components: {
        'modal': require('components/modal.vue')
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
                function(response) {
                    this.$.modal.close();
                }.bind(this)
            );
        }
    }
};
</script>
