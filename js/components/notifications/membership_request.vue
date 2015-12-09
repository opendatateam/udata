<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-users text-aqua"></span>
    {{ _('Pending membership request') }}
</a>
</template>

<script>
export default {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/organization/' + this.details.organization + '#membership-requests');
        }
    }
};
</script>
