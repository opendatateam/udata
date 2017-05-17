<style lang="less">
.image-picker-modal {
    .image-picker .uploader .drop-pane {
        border: 5px dashed white;
    }
}
</style>

<template>
<div>
<modal :title="title" class="image-picker-modal modal-info" v-ref:modal>
    <div class="modal-body">
        <picker v-ref:picker :endpoint="endpoint" :sizes="sizes"></picker>
    </div>
    <footer class="modal-footer">
        <button type="button" class="btn btn-primary btn-flat pull-left"
             v-show="$refs.picker && $refs.picker.resizing" @click="click">
            {{ _('Validate') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat" @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import Modal  from 'components/modal.vue';
import Picker from 'components/widgets/image-picker.vue';

export default {
    name: 'image-picker-modal',
    components: {Modal, Picker},
    props: {
        endpoint: String,
        sizes: {
            type: Array,
            default: () => [100],
        }
    },
    computed: {
        title() {
            return this.$refs.picker && this.$refs.picker.resizing
                ? this._('Resize your thumbnail')
                : this._('Upload an image');
        }
    },
    events: {
        'image:saved': function() {
            this.$refs.modal.close();
            return true;
        }
    },
    methods: {
        click() {
            this.$refs.picker.save();
        }
    }
};
</script>
