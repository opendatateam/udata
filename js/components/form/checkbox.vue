<style lang="less">
.checkbox-form-field label {
    font-weight: bold;
}
</style>

<template>
<div class="checkbox checkbox-form-field">
    <label :for="field.id" :class="{ 'required': required }">
        <input type="checkbox"
            :id="field.id"
            :name="field.id"
            :checked="value"
            @input="onChange"
            ></input>
        {{ field.label }}
    </label>
</div>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'Checkbox',
    mixins: [FieldComponentMixin],
    methods: {
        onChange(evt) {
            this.$dispatch('field:value-change', evt.target.checked);
        }
    }
};
</script>
