<template>
<div class="modal fade" tabindex="-1" role="dialog"
    aria-labelledby="modal-title" aria-hidden="true">
    <div class="modal-dialog" :class="{ 'modal-sm': size == 'sm', 'modal-lg': size == 'lg' }">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" @click="close">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <h4 class="modal-title" id="modal-title">{{title}}</h4>
            </div>
            <!-- Notifications -->
            <notification-zone class="modal-body"></notification-zone>
            <slot></slot>
        </div>
    </div>
</div>
</template>

<script>
import Modal from 'mixins/modal';
import NotificationZone from 'components/notification-zone.vue';

export default {
    replace: true,
    name: 'modal',
    props: ['title', 'size'],
    mixins: [Modal],
    components: {NotificationZone}
};
</script>

<style lang="less">
.modal {
    .notification-zone {
        padding: 0;

        .alert {
            border-radius: 0;
            margin: 0;
        }
    }
}
</style>
