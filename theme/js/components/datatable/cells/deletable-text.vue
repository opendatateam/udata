<template>
<del v-if="item.deleted"
    :title="_('This item has been deleted')"
    :datetime="item.deleted">{{value}}</del>
<span v-else>{{value}}</span>
</template>

<script>
export default {
    name: 'datatable-cell-deletable-text'
};
</script>
