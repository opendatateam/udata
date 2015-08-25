<template>
<div class="progress progress-sm">
    <span class="progress-bar progress-bar-{{ value < 9 ? value < 5 ? value < 2 ? 'danger' : 'warning' : 'primary' : 'success' }}" style="width: {{ value + 1 }}0%" title="_('Score:') {{ value }}"> </span>
</div>
</template>

<script>
export default {
    name: 'datatable-cell-progress-bars'
};
</script>
