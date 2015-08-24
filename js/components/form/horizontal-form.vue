<template>
    <form role="form" v-class="form-horizontal: 1">
        <form-field v-repeat="field:fields"></form-field>
    </form>
</template>

<script>
'use strict';

var BaseForm = require('components/form/base-form');

module.exports = {
    name: 'form-horizontal',
    mixins: [BaseForm],
    components: {
        'form-field': require('components/form/horizontal-field.vue')
    }
};
</script>
