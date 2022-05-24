<template>
    <MultiSelect
        :placeholder="$t('Schema')"
        :explanation="$t('Data schemas describe data models: what are the fields, how are data shown, what are the available values, etc. See schema.data.gouv.fr')"
        :searchPlaceholder="$t('Search a schema...')"
        :allOption="$t('All schemas')"
        :initialOptions="initialOptions"
        :values="values"
        :onChange="onChange"
    />
</template>

<script>
import { defineComponent } from "vue";
import getCatalog from "../../api/schemas";
import MultiSelect from "./multi-select.vue";

export default defineComponent({
    components: {
        MultiSelect,
    },
    props: {
        onChange: {
            type: Function,
            required: true,
        },
        values: {
            type: [String, Array],
        }
    },
    setup(props) {
        /** @type {Promise<import('../search/multi-select.vue').Option[]>} */
        const initialOptions = getCatalog().then(catalog => catalog.map(schema => ({
            label: schema.name,
            value: schema.name,
        })));
        return {initialOptions};
    }
});
</script>