<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-tasks text-aqua"></span>
    {{ _('Pending harvester validation for {name}', details) }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    methods: {
        click: function() {
            this.$go('/harvester/' + this.details.id + '/');
        }
    }
};
</script>
