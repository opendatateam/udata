import log from 'logger';
import $ from 'jquery';
import u from 'utils';
import Vue from 'vue';

/**
 * Base inheritable properties reusable by nested components
 */
export const FieldComponentMixin = {
    props: {
        field: {
            type: Object,
            default: function(){ return {};},
            required: true
        },
        model: Object,
        value: null,  // Means any type
        description: null,
        property: Object,
        required: Boolean,
        placeholder: String,
        readonly: Boolean
    }
};

/**
 * Common form fields behaviors
 */
export const BaseField = {
    name: 'base-field',
    replace: true,
    data: function() {
        return {
            errors: []
        };
    },
    components: {
        // Only register the common components
        'text-input': require('components/form/text-input.vue'),
        'hidden-input': require('components/form/hidden-input.vue'),
        'select-input': require('components/form/select-input.vue'),
        'markdown-editor': require('components/form/markdown-editor.vue'),
        'date-picker': require('components/form/date-picker.vue'),
        'checkbox': require('components/form/checkbox.vue')
    },
    props: {
        field: {
            type: Object,
            default: function(){ return {};},
            required: true
        },
        model: {
            type: Object,
            default: function(){ return {};},
            required: true
        },
        schema: {
            type: Object,
            default: function(){ return {};},
            required: true
        }
    },
    computed: {
        description: function() {
            let property = this.property;
            return property && property.hasOwnProperty('description')
                ? property.description
                : undefined;
        },
        property: function() {
            if (!this.schema.properties.hasOwnProperty(this.field.id)) {
                log.warn('Field "' + this.field.id + '" not found in schema');
                return {};
            }

            return this.schema.properties[this.field.id];
        },
        required: function() {
            if (!this.field || !this.schema.hasOwnProperty('required')) {
                return false;
            }
            return this.schema.required.indexOf(this.field.id) >= 0;
        },
        is_bool: function() {
            return this.property && this.property.type === 'boolean';
        },
        is_hidden: function() {
            return this.field && this.field.type === 'hidden';
        },
        value: function() {
            let value = '';
            if (this.model && this.field) {
                value = u.getattr(this.model, this.field.id);
                if (!value && this.property && this.property.hasOwnProperty('default')) {
                    value = this.property.default;
                }
            }
            return value || '';
        },
        placeholder: function() {
            return this.field.placeholder || this.field.label || '';
        },
        readonly: function() {
            return this.field.readonly || false;
        },
        widget: function() {
            let widget;
            if (this.field.widget) {
                widget = this.field.widget;
            } else if (this.property.type == 'boolean') {
                widget = 'checkbox';
            } else if (this.property.type == 'string') {
                if (this.property.format === 'markdown') {
                    widget = 'markdown-editor';
                } else if (this.property.enum) {
                    widget = 'select-input';
                }
            }
            widget = widget || 'text-input';

            // Lazy load component if needed
            if (!this.$options.components.hasOwnProperty(widget)) {
                this.$options.components[widget] = function(resolve, reject) {
                    require(['./' + widget + '.vue'], resolve);
                };
            }
            return widget;
        }
    },
    ready: function() {
        // Form help messages as popover on info sign
        $(this.$el).find('.form-help').popover({
            placement: 'left',
            trigger: 'hover',
            container: 'body',
            html: true
        });
    }
};

export default BaseField;
