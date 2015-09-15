<template>
<input type="hidden" v-attr="
    id: field.id,
    name: field.id,
    required: required,
    value: value"></input>
</template>

<script>
export default {
    name: 'hidden-input',
    replace: true,
    mixins: [require('components/form/base-field').FieldComponentMixin]
};
</script>
