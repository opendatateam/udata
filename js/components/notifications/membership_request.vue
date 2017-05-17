<template>
<a href @click.prevent="click">
    <span class="fa fa-fw fa-users text-aqua"></span>
    {{ _('Pending membership request') }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    methods: {
        click() {
            // Can't use v-link because of hash (only supported in vue-router 2.0)
            this.$go(`/organization/${this.details.organization}#membership-requests`);
        }
    }
};
</script>
