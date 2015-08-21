<style lang="less">

</style>

<template>
<select class="form-control" v-model="value" options="options" v-attr="
    id: field.id,
    name: field.id,
    placeholder: placeholder,
    required: required,
    disabled: readonly">
</select>
</template>

<script>
export default {
    name: 'select-input',
    inherit: true,
    replace: true,
    computed: {
        options: function() {
            if (!this.property && !this.field) return [];

            if (this.field.values) {
                return this.field.values;
            } else if (this.property.enum && this.field.labels)  {
                return this.property.enum.map(function(value) {
                    return {value: value, text: this.field.labels[value]};
                });
            } else if (this.property.enum)  {
                return this.property.enum.map(function(value) {
                    return {value: value, text: value};
                });
            }

            return [];
        }
    }
};
</script>
