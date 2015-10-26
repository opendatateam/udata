<template>
<input type="text" class="form-control" v-attr="
    id: field.id,
    name: field.id,
    placeholder: placeholder,
    required: required,
    value: value,
    readonly: readonly"></input>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'text-input',
    replace: true,
    mixins: [FieldComponentMixin]
};
</script>
