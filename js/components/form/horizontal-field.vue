<style lang="less">
.horizontal-field {
    .form-control {
        color: #555;
    }

    &.checkbox label {
        font-weight: bold;
    }
}
</style>

<template>
    <div class="horizontal-field" v-class="
        form-group: !is_bool,
        has-error: errors.length,
        checkbox: field_type == 'checkbox',
        radio: field_type == 'radio'
        ">
        <label for="{{field.id}}" v-class="required: required"
            class="col-sm-3 control-label">
            <input v-if="is_bool" v-attr="
                id: field.id,
                name: field.id,
                type: field_type,
                value: value"></input>
            <i v-if="errors.length" class="fa fa-times-circle-o"></i>
            {{ field.label }}
            <span v-show="property.description" class="form-help"
                v-attr="data-content: property.description"></span>
        </label>
        <div class="col-sm-9">
            <div v-component="{{widget}}"></div>
            <label for="{{field.id}}" class="help-block" v-repeat="errors"></label>
        </div>
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
    name: 'horizontal-form-field',
    mixins: [BaseField]
};
</script>
