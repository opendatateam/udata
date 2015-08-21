<style lang="less">

</style>

<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-users text-aqua"></span>
    {{ _('Pending membership request') }}
</a>
</template>

<script>
'use strict';

module.exports = {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/organization/' + this.details.organization + '#membership-requests');
        }
    }
};
</script>
