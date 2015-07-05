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
        checkbox: is_bool
        ">
        <label v-if="!is_bool" for="{{field.id}}" v-class="required: required"
            class="col-sm-3 control-label">
            <i v-if="errors.length" class="fa fa-times-circle-o"></i>
            {{ field.label }}
            <span v-show="property.description" class="form-help"
                v-attr="data-content: property.description"></span>
        </label>
        <div class="col-sm-9" v-class="col-sm-offset-3: is_bool">
            <component is="{{widget}}" v-if="!is_bool"></component>
            <input type="checkbox" v-if="is_bool" v-attr="
                id: field.id,
                name: field.id,
                value: value"></input>
            {{ is_bool ? field.label : '' }}
            <label for="{{field.id}}" class="help-block" v-repeat="errors"></label>
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
