<style>
.label {
    margin: 1px;
}
</style>

<template>
<span v-for="label in labels" class="label label-{{label | color}}">
    {{label | format}}
</span>
</template>

<script>
export default {
    name: 'datatable-cell-label',
    filters: {
        format(value) {
            return this.field.hasOwnProperty('label_func')
                ? this.field.label_func(value)
                : value;
        },
        color(value) {
            return this.field.hasOwnProperty('label_type')
                ? this.field.label_type(value)
                : 'default'
        },
    },
    computed: {
        labels() {
            return this.value instanceof Array
                ? this.value
                : [this.value]
        }
    }
};
</script>
