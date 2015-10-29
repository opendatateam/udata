<style lang="less">
.form-control {
    color: #555;
}
</style>

<template>
    <form role="form">
        <field v-for="field in fields" :field="field"
            :schema="schema" :model="model">
        </field>
    </form>
</template>

<script>
'use strict';

var BaseForm = require('components/form/base-form');

module.exports = {
    name: 'form-vertical',
    mixins: [BaseForm],
    components: {
        field: require('components/form/vertical-field.vue')
    }
};
</script>
