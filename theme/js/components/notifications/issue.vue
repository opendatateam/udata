<template>
<a v-link="link">
    <span class="fa fa-fw fa-warning text-yellow"></span>
    {{ details.title }}
</a>
</template>

<script>
import BaseNotification from 'components/notifications/base';

export default {
    mixins: [BaseNotification],
    computed: {
        link() {
            const subject = this.details.subject;
            return {name: `${subject.type}-issue`, params: {
                oid: subject.id,
                issue_id: this.details.id,
            }};
        }
    }
};
</script>
