<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-comment text-purple"></span>
    {{ details.title }}
</a>
</template>

<script>
export default {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/discussion/' + this.details.id + '/');
        }
    }
};
</script>
