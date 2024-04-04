<template>
<input type="number" class="form-control"
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
    name: 'number-input',
    mixins: [FieldComponentMixin],
};
</script>
