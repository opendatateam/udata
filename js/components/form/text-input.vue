<style lang="less">

</style>

<template>
<input type="text" class="form-control" v-attr="
    id: field.id,
    name: field.id,
    placeholder: placeholder,
    required: required,
    value: value,
    readonly: readonly || false"></input>
</template>

<script>
'use strict';

module.exports = {
    name: 'text-input',
    replace: true,
    mixins: [require('components/form/base-field').FieldComponentMixin]
};
</script>
