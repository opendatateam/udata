<style lang="less">

</style>

<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-warning text-yellow"></span>
    {{ details.title }}
</a>
</template>

<script>
'use strict';

module.exports = {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/issue/' + this.details.id + '/');
        }
    }
};
</script>
