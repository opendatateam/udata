<template>
<div v-show="$root.notifications && $root.notifications.length > 0" class="notification-zone">
    <alert v-for="n in $root.notifications" :alert="n"></alert>
</div>
</template>

<script>
import Alert from 'components/alert.vue';

export default {
    name: 'notification-zone',
    components: {Alert}
};
</script>

<style lang="less">
.notification-zone {
    padding: 15px 15px 0;
    position: fixed;
    right: 15px;
    bottom: 15px;
    width: 350px;
    z-index: 10000;

    .alert {
        &:last-child {
            margin-bottom: 0;
        }

        &:not(:last-child) {
            margin-bottom: 5px;
        }
    }
}
</style>
