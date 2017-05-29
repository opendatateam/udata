<template>
<a href @click.prevent="click">
    <span class="fa fa-fw fa-exchange text-primary"></span>
    <span>{{ _('Pending transfer request') }}</span>
</a>
</template>

<script>
import Vue from 'vue';
import BaseNotification from 'components/notifications/base';
import ResponseModal from 'components/transfer/response-modal.vue';

export default {
    mixins: [BaseNotification],
    methods: {
        click() {
            this.$root.$modal(ResponseModal, {transferid: this.details.id});
        }
    }
};
</script>
