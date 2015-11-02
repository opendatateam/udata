<style lang="less">
.image-picker-modal {
    .image-picker .uploader .drop-pane {
        border: 5px dashed white;
    }
}
</style>

<template>
<modal :title="title" class="image-picker-modal modal-info" v-ref:modal>
    <div class="modal-body">
        <picker v-ref:picker :endpoint="endpoint" :sizes="sizes"></picker>
    </div>
    <footer class="modal-footer">
        <button type="button" class="btn btn-primary btn-flat pointer pull-left"
             v-show="$refs.picker && $refs.picker.resizing" @click="click">
            {{ _('Validate') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat pointer" data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
export default {
    data: function() {
        return {
            endpoint: null,
            sizes: [100]
        };
    },
    computed: {
        title: function() {
            return this.$refs.picker && this.$refs.picker.resizing
                ? this._('Resize your thumbnail')
                : this._('Upload an image');
        }
    },
    components: {
        modal: require('components/modal.vue'),
        picker: require('components/widgets/image-picker.vue')
    },
    events: {
        'image:saved': function() {
            this.$refs.modal.close();
            return true;
        }
    },
    methods: {
        click: function() {
            this.$refs.picker.save();
        }
    }
};
</script>
