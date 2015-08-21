<style lang="less">

</style>

<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-comment text-purple"></span>
    {{ details.title }}
</a>
</template>

<script>
'use strict';

module.exports = {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/discussion/' + this.details.id + '/');
        }
    }
};
</script>
