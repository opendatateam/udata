<template>
<a v-link="link">
    <span class="fa fa-fw fa-tasks text-aqua"></span>
    {{ _('Pending harvester validation for {name}', details) }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    computed: {
        link() {
            return {name: 'harvester', params: {oid: this.details.id}};
        }
    }
};
</script>
