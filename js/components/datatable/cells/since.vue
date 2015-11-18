<template>
<time :datetime="value">{{value | since}}</time>
</template>

<script>
export default {
    name: 'datatable-cell-since'
};
</script>
