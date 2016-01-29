<style lang="less">
.datatable {
    td.avatar-cell {
        padding: 3px;
    }
}
</style>

<template>
<img :src="src" :width="field.width" :height="field.width" />
</template>

<script>
import $ from 'jquery';
import placeholders from 'helpers/placeholders';

export default {
    name: 'datatable-cell-avatar',
    attached: function() {
        // Dirty hack to fix class on field/td iteration
        $(this.$el).closest('td').addClass('avatar-cell');
    },
    computed: {
        src: function() {
            if (this.value) {
                return this.value;
            } else if (this.field.placeholder) {
                return placeholders.getFor(this.field.placeholder);
            } else {
                return placeholders.generic;
            }
        }
    }
};
</script>
