<template>
<a class="pointer" v-on="click: click">
    <span class="fa fa-fw fa-tasks text-aqua"></span>
    {{ _('Pending harvester validation for __name__', details) }}
</a>
</template>

<script>
export default {
    mixins: [require('components/notifications/base')],
    methods: {
        click: function() {
            this.$go('/harvester/' + this.details.id + '#validate');
        }
    }
};
</script>
