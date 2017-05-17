<style lang="less">
.form-control {
    color: #555;
}
</style>

<template>
    <form role="form" v-el:form>
        <field v-for="field in fields" :field="field"
            :schema="schema" :model="model">
        </field>
    </form>
</template>

<script>
import BaseForm from 'components/form/base-form';
import Field from 'components/form/vertical-field.vue';

export default {
    name: 'vertical-form',
    mixins: [BaseForm],
    components: {Field}
};
</script>
