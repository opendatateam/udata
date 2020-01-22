<template>
<div>
    <v-form v-ref:form :fields="fields" :model="source"></v-form>
    <config-form v-ref:config-form :config="source.config || {}" :backend="backend"></config-form>
    <v-form v-ref:post-form :fields="postFields" :model="source"></v-form>
</div>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import backends from 'models/harvest/backends';
import VForm from 'components/form/vertical-form.vue';
import ConfigForm from './config-form.vue';

export default {
    name: 'HarvestSourceForm',
    components: {VForm, ConfigForm},
    props: {
        source: {
            type: HarvestSource,
            default() {
                return new HarvestSource();
            }
        }
    },
    data() {
        return {
            backends: backends.items,
            backendValue: this.source.backend,
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'url',
                    label: this._('URL'),
                    widget: 'url-field',
                }, {
                    id: 'backend',
                    label: this._('Backend'),
                    widget: 'select-input',
                    values: this.backendValues
                }],
            postFields: [{
                id: 'active',
                label: this._('Active')
            }, {
                id: 'autoarchive',
                label: this._('Automatic archiving')
            }],
            filters: [],
        };
    },
    events: {
        'field:change': function(field, value) {
            if (field.field.id === 'backend') {
                this.backendValue = value;
            }
            return true;  // Let the event continue its bubbling
        },
        'form:change': function(form) {
            if (form.validate()) {
                this.$dispatch('harvest:source:form:changed', this.serialize());
            }
            return true;  // Let the event continue its bubbling
        }
    },
    computed: {
        /**
         * The currently selected backend
         */
        backend() {
            if (!this.backendValue) return;
            return this.backends.find(item => item.id === this.backendValue);
        },
        /**
         * Values for the backend select box
         */
        backendValues() {
            return this.backends.map(item => ({value: item.id, text: item.label}));
        },
    },
    created() {
        // Prevent empty backends select box
        backends.$on('updated', () => {this.backends = backends.items;});
    },
    methods: {
        serialize() {
            const data =  Object.assign({},
                this.$refs.postForm.serialize(),
                this.$refs.form.serialize(),
            );
            data.config = this.$refs.configForm.serialize();
            return data;
        },
        validate() {
            return this.$refs.form.validate();
        }
    }
};
</script>
