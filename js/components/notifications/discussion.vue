<template>
<a v-link="link">
    <span class="fa fa-fw fa-comment text-purple"></span>
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
            return {name: `${subject.type}-discussion`, params: {
                oid: subject.id,
                discussion_id: this.details.id,
            }};
        }
    }
};
</script>
