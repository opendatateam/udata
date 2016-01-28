<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-exchange text-primary"></span>
    <span>{{ _('Pending transfer request') }}</span>
</a>
</template>

<script>
import Vue from 'vue';
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    methods: {
        click: function() {
            this.$root.$modal(
                require('components/transfer/response-modal.vue'),
                {transferid: this.details.id}
            );
        }
    }
};
</script>
