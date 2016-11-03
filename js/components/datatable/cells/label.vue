<style>
.label {
    margin: 1px;
}
</style>

<template>
<span v-for="label in labels" class="label label-{{color(label)}}">
    {{format(label)}}
</span>
</template>

<script>
export default {
    name: 'datatable-cell-label',
    methods: {
        format: function(value) {
            return this.field.hasOwnProperty('label_func')
                ? this.field.label_func(value)
                : value;
        },
        color: function(value) {
            return this.field.hasOwnProperty('label_type')
                ? this.field.label_type(value)
                : 'default'
        },
    },
    computed: {
        labels: function() {
            let values = this.value
            // If the field does not contain a list, we cast it
            // so that the template, which assumes a list, provides
            // the right rendering
            if (values instanceof Array === false) {
                values = [values]
            }
            return values
        }
    }
};
</script>
