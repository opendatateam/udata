<template>
<input type="hidden"
    :id="field.id"
    :name="field.id"
    :value="value"
    :required="required"></input>
</template>

<script>
export default {
    name: 'hidden-input',
    replace: true,
    mixins: [require('components/form/base-field').FieldComponentMixin]
};
</script>
