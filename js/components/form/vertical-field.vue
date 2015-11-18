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
    <div class="vertical-field" :class="{
        'form-group': !is_bool && !is_hidden,
        'has-error': errors.length
        }">
        <span v-show="description" class="form-help"
            :data-content="description"
            v-if="!is_hidden"></span>
        <label :for="field.id" :class="{ 'required': required }"
            v-if="!is_hidden && !is_bool">
            {{ field.label }}
        </label>
        <component :is="widget"
            :field="field" :value="value" :model="model"
            :description="description" :property="property"
            :placeholder="placeholder" :required="required"
            :readonly="readonly">
        </component>
        <label :for="field.id" class="help-block"
            v-for="error in errors">{{error}}</label>
    </div>
</template>

<script>
import {BaseField} from 'components/form/base-field';

export default {
    name: 'vertical-form-field',
    mixins: [BaseField],
};
</script>
