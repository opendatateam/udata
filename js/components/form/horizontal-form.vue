<template>
    <form role="form" class="form-horizontal" v-el:form>
        <field v-for="field in fields" :field="field" track-by="id"
            :schema="schema" :model="model"></field>
    </form>
</template>

<script>
import BaseForm from 'components/form/base-form';
import Field from 'components/form/horizontal-field.vue';

export default {
    name: 'form-horizontal',
    mixins: [BaseForm],
    components: {Field},
};
</script>
