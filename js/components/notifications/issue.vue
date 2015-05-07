<style lang="less">

</style>

<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-warning text-yellow"></span>
    <span>{{ _('Issue') }}</span>
</a>
</template>

<script>
'use strict';

module.exports = {
    data: function() {
        return {};
    },
    methods: {
        click: function() {
            this.$go('/issue/' + this.details.id + '/');
        }
    }
};
</script>
