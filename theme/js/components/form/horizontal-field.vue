<style lang="less">
.horizontal-field {
    .form-control {
        color: #555;
    }

    label.help-block {
        margin-bottom: 0;
    }
}
</style>

<template>
    <div class="horizontal-field" :class="{
        'form-group': !is_hidden,
        'has-error': errors.length,
        'has-success': success,
        }">
        <label v-if="!is_hidden" :for="field.id"
            :class="{ 'required': required && !is_bool }"
            class="col-sm-3 control-label">
            <i v-if="errors.length" class="fa fa-times-circle-o"></i>
            {{ is_bool ? '' : field.label }}
            <span v-if="!is_hidden" v-show="description" class="form-help"
                v-popover="description" popover-trigger="hover" popover-placement="left">
            </span>
        </label>
        <div class="col-sm-9">
            <component :is="widget"
                :field="field" :value="value" :model="model"
                :description="description" :property="property"
                :placeholder="placeholder" :required="required"
                :readonly="readonly">
            </component>
            <label :for="field.id" class="help-block"
                v-for="error in errors" track-by="$index">{{error}}</label>
        </div>
    </div>
</template>

<script>
import {BaseField} from 'components/form/base-field';

export default {
    name: 'horizontal-form-field',
    mixins: [BaseField]
};
</script>
