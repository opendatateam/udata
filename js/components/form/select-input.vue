<style lang="less">

</style>

<template>
<select class="form-control" v-attr="
    id: field.id,
    name: field.id,
    placeholder: placeholder,
    required: required,
    disabled: readonly">
    <option v-repeat="o:options"
        v-attr="selected: value == o.value">{{ o.label }}</option>
</select>
</template>

<script>
'use strict';

module.exports = {
    name: 'select-input',
    inherit: true,
    replace: true,
    computed: {
        options: function() {
            if (!this.property) return [];

            if (this.property.enum && this.field.labels)  {
                return this.property.enum.map(function(value) {
                    return {value: value, label: this.field.labels[value]};
                });
            } else if (this.property.enum)  {
                return this.property.enum.map(function(value) {
                    return {value: value, label: value};
                });
            } else if (this.field.values) {
                return this.field.values;
            }

            return [];
        }
    },
    filters: {
        label: function(value) {
            if (this.field.labels) {
                return this.field.labels[value];
            }
            return value
        },
        is_selected: function(value) {
            if (this.value != undefined) {
                return value == this.value;
            } else if (this.field && this.field.hasOwnProperty('default')) {
                return value == this.filed.default;
            }
            return false;
        }
    }
};
</script>
