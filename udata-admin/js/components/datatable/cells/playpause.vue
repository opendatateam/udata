<template>
<i class="fa fa-fw fa-{{value ? 'play' : 'stop'}} text-{{value ? 'green' : 'red'}}"></i>
</template>

<script>
export default {
    name: 'datatable-cell-playpause',
    default: false,
};
</script>
