<template>
<div class="modal fade" tabindex="-1" role="dialog"
    aria-labelledby="modal-title" aria-hidden="true">
    <div class="modal-dialog" v-class="modal-sm: size == 'sm', modal-lg: size == 'lg'">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <h4 class="modal-title" id="modal-title">{{title}}</h4>
            </div>
            <content></content>
        </div>
    </div>
</div>
</template>

<script>
import $ from 'jquery';

export default {
    replace: true,
    name: 'modal',
    props: ['title', 'size'],
    events: {
        'modal:close': function() {
            this.close();
        }
    },
    ready: function() {
        $(this.$el).modal().on('hidden.bs.modal', () => {
            this.$destroy(true);
        });
    },
    methods: {
        close: function() {
            $(this.$el).modal('hide');
        }
    }
};
</script>
