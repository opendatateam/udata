<style lang="less">
.datatable {
    td.avatar-cell {
        padding: 3px;
    }
}
</style>

<template>
<img :src="value | avatar_url field.width" :width="field.width" :height="field.width" />
</template>

<script>
export default {
    attached() {
        // Dirty hack to fix class on field/td iteration
        this.$el.closest('td').classList.add('avatar-cell');
    }
};
</script>
