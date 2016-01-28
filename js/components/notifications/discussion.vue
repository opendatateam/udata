<template>
<a class="pointer" @click="click">
    <span class="fa fa-fw fa-comment text-purple"></span>
    {{ details.title }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    methods: {
        click: function() {
            let id = this.details.id,
                subject = this.details.subject,
                route = `/${subject.type}/${subject.id}/discussion/${id}/`;
            this.$go(route);
        }
    }
};
</script>
