<template>
<div class="progress progress-sm">
    <span class="progress-bar progress-bar-{{ progress_class }}"
        :style="{width: value * 100 + '%'}"
        :title="_('Score:') + ' ' + value * 100">
    </span>
</div>
</template>

<script>
export default {
    name: 'datatable-cell-progress-bars',
    computed: {
        progress_class: function() {
            if (this.value < 1/3) {
                return 'danger';
            }
            else if (this.value < 2/3) {
                return 'warning';
            }
            else if (this.value < 0.9) {
                return 'primary';
            }
            else {
                return 'success';
            }
        }
    }
};
</script>
