<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-warning text-yellow"></span>
    {{ details.title }}
</a>
</template>

<script>
export default {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/issue/' + this.details.id + '/');
        }
    }
};
</script>
