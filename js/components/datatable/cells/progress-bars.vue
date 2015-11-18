<template>
<div class="progress progress-sm">
    <span class="progress-bar progress-bar-{{ progress_class }}"
        :style="{width: value + 1 + '0%'}"
        :title="_('Score:') + ' ' + value">
    </span>
</div>
</template>

<script>
export default {
    name: 'datatable-cell-progress-bars',
    computed: {
        progress_class: function() {
            if (this.value < 2) {
                return 'danger';
            }
            else if (this.value < 5) {
                return 'warning';
            }
            else if (this.value < 9) {
                return 'primary';
            }
            else {
                return 'success';
            }
        }
    }
};
</script>
