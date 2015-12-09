<template>
<time :datetime="value | dt YYYY-MM-DD">{{value | dt L}}</time>
</template>

<script>
export default {
    name: 'datatable-cell-date',
};
</script>
