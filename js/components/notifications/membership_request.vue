<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-users text-aqua"></span>
    {{ _('Pending membership request') }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    methods: {
        click: function() {
            this.$go('/organization/' + this.details.organization + '#membership-requests');
        }
    }
};
</script>
