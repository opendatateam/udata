<style lang="less">
.image-picker-modal {
    .image-picker .uploader .drop-pane {
        border: 5px dashed white;
    }
}
</style>

<template>
<modal title="{{ title }}" class="image-picker-modal modal-info"
    v-ref="modal">
    <div class="modal-body">
        <image-picker v-ref="picker" endpoint="{{endpoint}}" sizes="{{sizes}}">
        </image-picker>
    </div>
    <footer class="modal-footer">
        <button type="button" class="btn btn-primary btn-flat pointer pull-left"
             v-if="$.picker.resizing" v-on="click: click">
            {{ _('Validate') }}
        </button>
        <button type="button" class="btn btn-warning btn-flat pointer" data-dismiss="modal">
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
            endpoint: null,
            sizes: [100]
        };
    },
    computed: {
        title: function() {
            return this.$.picker && this.$.picker.resizing
                ? this._('Resize your thumbnail')
                : this._('Upload an image');
        }
    },
    components: {
        'modal': require('components/modal.vue'),
        'image-picker': require('components/widgets/image-picker.vue')
    },
    events: {
        'image:saved': function() {
            this.$.modal.close();
        }
    },
    methods: {
        click: function() {
            this.$.picker.save();
        }
    }
};
</script>
