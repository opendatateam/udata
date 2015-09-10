<template>
    <form role="form" v-class="form-horizontal: 1">
        <field v-repeat="field in fields"
            schema="{{schema}}" model="{{model}}"></field>
    </form>
</template>

<script>
'use strict';

var BaseForm = require('components/form/base-form');

module.exports = {
    name: 'form-horizontal',
    mixins: [BaseForm],
    components: {
        field: require('components/form/horizontal-field.vue')
    }
};
</script>
