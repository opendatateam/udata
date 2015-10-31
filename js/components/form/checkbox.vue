<style lang="less">
.checkbox label {
    font-weight: bold;
}
</style>

<template>
<div class="checkbox">
    <label :for="field.id" :class="{ 'required': required }">
        <input type="checkbox"
            :id="field.id"
            :name="field.id"
            :checked="value"
            ></input>
        {{ field.label }}
    </label>
</div>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'Checkbox',
    replace: true,
    mixins: [FieldComponentMixin]
};
</script>
