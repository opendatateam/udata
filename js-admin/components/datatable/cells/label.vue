<template>
<span class="label label-{{color}}">{{label}}</span>
</template>

<script>
export default {
    name: 'datatable-cell-label',
    computed: {
        color: function() {
            return this.field.label_type(this.value);
        },
        label: function() {
            return this.field.hasOwnProperty('label_func')
                ? this.field.label_func(this.value)
                : this.value;
        }
    }
};
</script>
