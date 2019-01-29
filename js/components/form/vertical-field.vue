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
        'has-error': errors.length,
        'has-success': success,
        }">
        <span v-if="!is_hidden" v-show="description" class="form-help"
            v-popover="description" popover-trigger="hover" popover-placement="left">
        </span>
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
            v-for="error in errors" track-by="$index">{{error}}</label>
    </div>
</template>

<script>
import {BaseField} from 'components/form/base-field';

export default {
    name: 'vertical-form-field',
    mixins: [BaseField],
};
</script>
