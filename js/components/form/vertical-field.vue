<style lang="less">
.form-control {
    color: #555;
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
        form-group: !is_bool && !is_hidden,
        has-error: errors.length
        ">
        <span v-show="description" class="form-help"
            v-attr="data-content: description"
            v-if="!is_hidden"></span>
        <label for="{{field.id}}" v-class="required: required"
            v-if="!is_hidden && !is_bool">
            {{ field.label }}
        </label>
        <component is="{{widget}}"
            field="{{field}}" model="{{model}}" value="{{value}}"
            description="{{description}}" property="{{property}}"
            placeholder="{{placeholder}}" required="{{required}}">
        </component>
        <label for="{{field.id}}" class="help-block" v-repeat="errors"></label>
    </div>
</template>

<script>
import {BaseField} from 'components/form/base-field';

export default {
    name: 'vertical-form-field',
    mixins: [BaseField],
};
</script>
