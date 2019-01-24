import log from 'logger';
import u from 'utils';
import Vue from 'vue';

/**
 * Base inheritable properties reusable by nested components
 */
export const FieldComponentMixin = {
    props: {
        field: {
            type: Object,
            default() { return {};}
        },
        model: Object,
        value: null,  // Means any type
        description: null,
        property: Object,
        required: Boolean,
        placeholder: String,
        readonly: Boolean
    },
    methods: {
        onChange(evt) {
            this.$dispatch('field:value-change', evt.target.value);
        }
    }
};

/**
 * Common form fields behaviors
 */
export const BaseField = {
    name: 'base-field',
    data() {
        return {
            errors: [],
            isField: true,
        };
    },
    components: {
        // Only register the common components
        'text-input': require('components/form/text-input.vue'),
        'number-input': require('components/form/number-input.vue'),
        'hidden-input': require('components/form/hidden-input.vue'),
        'select-input': require('components/form/select-input.vue'),
        'markdown-editor': require('components/form/markdown-editor.vue'),
        'date-picker': require('components/form/date-picker.vue'),
        'checkbox': require('components/form/checkbox.vue')
    },
    events: {
        'field:value-change': function(value) {
            this.$dispatch('field:change', this, value);
            return true;  // Let the event continue its bubbling
        }
    },
    props: {
        field: {
            type: Object,
            default() { return {};},
            required: true
        },
        model: {
            type: Object,
            default() { return {};},
            required: true
        },
        schema: {
            type: Object,
            default() { return {};},
            required: true
        }
    },
    computed: {
        description() {
            const property = this.property;
            return property && property.hasOwnProperty('description')
                ? property.description
                : undefined;
        },
        property() {
            if (!this.schema.properties.hasOwnProperty(this.field.id)) {
                log.warn('Field "' + this.field.id + '" not found in schema');
                return {};
            }

            return this.schema.properties[this.field.id];
        },
        required() {
            if (!this.field || !this.schema.hasOwnProperty('required')) {
                return false;
            }
            return this.schema.required.indexOf(this.field.id) >= 0;
        },
        is_bool() {
            return this.property && this.property.type === 'boolean';
        },
        is_hidden() {
            return this.field && this.field.type === 'hidden';
        },
        value() {
            let value;
            if (this.model && this.field) {
                value = u.getattr(this.model, this.field.id);
            }
            if ((value === undefined || value === null) && this.property && this.property.hasOwnProperty('default')) {
                value = this.property.default;
            }
            return value;
        },
        placeholder() {
            return this.field.placeholder || this.field.label || '';
        },
        readonly() {
            return this.field.readonly || false;
        },
        widget() {
            let widget;
            if (this.field.widget) {
                widget = this.field.widget;
            } else if (this.property.type === 'boolean') {
                widget = 'checkbox';
            } else if (this.property.type === 'integer') {
                widget = 'number-input';
            } else if (this.property.type === 'string') {
                if (this.property.format === 'markdown') {
                    widget = 'markdown-editor';
                } else if (this.property.enum) {
                    widget = 'select-input';
                }
            }
            widget = widget || 'text-input';

            // Lazy load component if needed
            if (!Vue.util.resolveAsset(this.$options, 'components', widget)) {
                this.$options.components[widget] = function(resolve, reject) {
                    require(['./' + widget + '.vue'], resolve);
                };
            }
            return widget;
        }
    },
    watch: {
        value(value) {
            this.$dispatch('field:change', this, value);
        }
    }
};

export default BaseField;
