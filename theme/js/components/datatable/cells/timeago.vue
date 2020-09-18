<template>
<time :datetime="value" class="timeago">{{value | timeago}}</time>
</template>

<script>
export default {
    name: 'datatable-cell-timeago'
};
</script>
