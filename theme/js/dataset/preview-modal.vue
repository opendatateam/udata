<template>
<modal class="preview-modal" v-ref:modal :title="_('Preview')" large>

    <div class="modal-body">
        <iframe :src="url" width="100%" height="600" frameborder="0"></iframe>
    </div>

    <footer class="modal-footer text-center">
        <button class="btn btn-default" @click="$refs.modal.close">
            {{ _('Close') }}
        </button>
    </footer>
</modal>
</template>

<script>
import Modal from 'components/modal.vue';

export default {
    props: {
        url: String
    },
    components: {Modal}
};
</script>

<style lang="less">
@import "~less/udata/variables.less";

.preview-modal {
    .modal-dialog {
        @media (min-width: @screen-sm-min) {
            // Full width on sm+ devices
            width: 99%;
        }
    }

    .modal-body {
        // Thinner padding
        padding: 1px;
    }
}
</style>
