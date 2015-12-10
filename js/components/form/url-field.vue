<template>
<div>
    <input type="url" class="form-control"
        :id="field.id"
        :name="field.id"
        :placeholder="placeholder"
        :required="required"
        :readonly="readonly"
        :value="value"></input>
</div>
</template>

<script>
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'url-field',
    replace: true,
    mixins: [FieldComponentMixin],
};
</script>
