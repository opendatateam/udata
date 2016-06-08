<template>
<input type="hidden"
    :id="field.id"
    :name="field.id"
    :value="value"
    :required="required"></input>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'hidden-input',
    replace: true,
    mixins: [FieldComponentMixin]
};
</script>
