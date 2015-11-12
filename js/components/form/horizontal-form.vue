<template>
    <form role="form" :class="{ 'form-horizontal': 1 }" v-el:form>
        <field v-for="field in fields" :field="field"
            :schema="schema" :model="model"></field>
    </form>
</template>

<script>
import BaseForm from 'components/form/base-form';

export default {
    name: 'form-horizontal',
    mixins: [BaseForm],
    components: {
        field: require('components/form/horizontal-field.vue')
    }
};
</script>
