import log from 'logger';
import $ from 'jquery';
import u from 'utils';

/**
 * Common form fields behaviors
 */
export default {
    name: 'base-field',
    replace: true,
    inherit: true,
    data: function() {
        return {
            errors: []
        };
    },
    components: {
        'text-input': require('components/form/text-input.vue'),
        'hidden-input': require('components/form/hidden-input.vue'),
        'select-input': require('components/form/select-input.vue'),
        'markdown-editor': require('components/form/markdown.vue'),
        'tag-completer': require('components/form/tag-completer'),
        'dataset-completer': require('components/form/dataset-completer'),
        'reuse-completer': require('components/form/reuse-completer'),
        'territory-completer': require('components/form/territory-completer'),
        'zone-completer': require('components/form/zone-completer.vue'),
        'format-completer': require('components/form/format-completer'),
        'datetime-picker': require('components/form/datetime-picker.vue'),
        'time-picker': require('components/form/time-picker.vue'),
        'date-picker': require('components/form/date-picker.vue'),
        'daterange-picker': require('components/form/daterange-picker.vue'),
        'checksum': require('components/form/checksum.vue'),
        'checkbox': require('components/form/checkbox.vue')
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
        widget: function() {
            if (this.field.widget) {
                return this.field.widget;
            }
            switch(this.property.type) {
                case 'boolean':
                    return 'checkbox';
                case 'string':
                    if (this.property.format === 'markdown') {
                        return 'markdown-editor';
                    } else if (this.property.enum) {
                        return 'select-input';
                    }
                default:
                    return 'text-input';
            }
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
