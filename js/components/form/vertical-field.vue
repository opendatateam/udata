<style lang="less">
.form-control {
    color: #555;
}
.checkbox label {
    font-weight: bold;
}

.vertical-field {
    .form-help {
        float: right;
        clear: both;
    }
}
</style>

<template>
    <div class="vertical-field" v-class="
        form-group: !is_bool,
        has-error: errors.length,
        checkbox: field_type == 'checkbox',
        radio: field_type == 'radio',
        ">
        <span v-show="property.description" class="form-help"
            v-attr="data-content: property.description"
            v-if="field.type!=='hidden'"></span>
        <label for="{{field.id}}" v-class="required: required"
            v-if="field.type!=='hidden'">
            {{ field.label }}
        </label>
        <input v-if="is_bool" v-attr="
            id: field.id,
            name: field.id,
            type: field_type,
            value: value"></input>
        <component is="{{widget}}"></component>
        <label for="{{field.id}}" class="help-block" v-repeat="errors"></label>
        <div class="{{type}}" v-if="is_bool">
            <label>
            </label>
        </div>
    </div>
</template>

<script>
'use strict';

var BaseField = require('components/form/base-field');

module.exports = {
    name: 'vertical-form-field',
    mixins: [BaseField]
};
</script>
