<template>
<span class="badge" :class="{
    'bg-green': value > 0,
    'bg-red': value == 0
    }">{{value}}</span>
</template>

<script>
export default {
    name: 'datatable-cell-metric',
    default: 0
};
</script>
