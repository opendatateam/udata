<template>
<div v-show="$root.notifications && $root.notifications.length > 0" class="notification-zone">
    <alert v-for="n in $root.notifications" :alert="n"></alert>
</div>
</template>

<script>
import Alert from 'components/alert.vue';
export default {
    replace: true,
    components: {Alert}
};
</script>

<style lang="less">
.notification-zone {
    padding: 15px 15px 0;

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
