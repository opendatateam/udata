<template>
<div class="modal fade" tabindex="-1" role="dialog"
    aria-labelledby="modal-title" aria-hidden="true" @click="onBackdropClick">
    <div v-el:modal class="modal-dialog" :class="{ 'modal-sm': small, 'modal-lg': large }">
        <slot name="modal-content">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" @click="close">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <h4 class="modal-title" id="modal-title">{{title}}</h4>
            </div>
            <slot></slot>
        </div>
        </slot>
    </div>
</div>
</template>

<script>
import velocity from 'velocity-animate';
import {getScrollBarWidth} from 'vue-strap/src/utils/utils.js';

export default {
    name: 'modal',
    props: {
        title: {type: String, default: ''},
        small: {type: Boolean, default: false},
        large: {type: Boolean, default: false},
        visible: {type: Boolean, default: true},
    },
    ready() {
        this.setVisiblity(this.visible);
    },
    methods: {
        show() {
            this.visible = true;
            return this;
        },
        close() {
            this.visible = false;
            return this;
        },
        setVisiblity(visible) {
            if (visible) {
                const scrollbarWidth = getScrollBarWidth();
                document.body.classList.add('modal-open');
                this.$dispatch('modal:open');
                this.$el.classList.add('in');
                velocity(this.$els.modal, 'slideDown', {duration: 300}).then(() => {
                    this.$els.modal.focus();
                    this.$dispatch('modal:opened');
                });
                if (scrollbarWidth !== 0) {
                    document.body.style.paddingRight = `${scrollbarWidth}px`;
                }
            } else {
                document.body.style.paddingRight = null
                this.$dispatch('modal:close');
                velocity(this.$els.modal, 'slideUp', {duration: 300}).then(() => {
                    document.body.classList.remove('modal-open');
                    this.$el.classList.remove('in');
                    this.$dispatch('modal:closed');
                });
            }
        },
        onBackdropClick(event) {
            if (event.target === this.$el) this.close();
        }
    },
    watch: {
        visible(visible) {
            this.setVisiblity(visible);
        }
    }
};
</script>

<style lang="less">
.modal {
    transition: all 0.3s ease;
    background: rgba(0, 0, 0, 0.4);

    &.in {
        display: block;
    }

    .modal-dialog {
        display: none;
    }

    .notification-zone {
        padding: 0;

        .alert {
            border-radius: 0;
            margin: 0;
        }
    }
}
</style>
