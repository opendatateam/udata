<template>
<input type="text" class="form-control"
    :id="field.id"
    :name="field.id"
    :placeholder="placeholder"
    :required="required"
    :readonly="readonly"
    :value="value"
    @input="onChange"></input>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'text-input',
    mixins: [FieldComponentMixin],
};
</script>
