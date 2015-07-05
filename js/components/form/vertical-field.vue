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
        checkbox: is_bool
        ">
        <span v-show="property.description" class="form-help"
            v-attr="data-content: property.description"
            v-if="field.type!=='hidden'"></span>
        <label for="{{field.id}}" v-class="required: required"
            v-if="field.type!=='hidden'">
            <input type="checkbox" v-if="is_bool" v-attr="
                id: field.id,
                name: field.id,
                checked: value"></input>
            {{ field.label }}
        </label>
        <component is="{{widget}}" v-if="!is_bool"></component>
        <label for="{{field.id}}" class="help-block" v-repeat="errors"></label>
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
