<template>
<time :datetime="value">{{value | dt L LT}}</time>
</template>

<script>
export default {
    name: 'datatable-cell-datetime'
};
</script>
