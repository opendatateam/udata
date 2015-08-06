define(['logger', 'jquery'], function(log, $) {
    'use strict';

    return {
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
            'license-completer': require('components/form/license-completer'),
            'territory-completer': require('components/form/territory-completer'),
            'zone-completer': require('components/form/zone-completer.vue'),
            'format-completer': require('components/form/format-completer'),
            'datetime-picker': require('components/form/datetime-picker.vue'),
            'time-picker': require('components/form/time-picker.vue'),
            'date-picker': require('components/form/date-picker.vue'),
            'daterange-picker': require('components/form/daterange-picker.vue'),
            'checksum': require('components/form/checksum.vue')
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
                    log.error('Field "' + this.field.id + '" not found in schema');
                    return {};
                }

                return this.schema.properties[this.field.id];
            },
            required: function() {
                if (!this.field) {
                    return false;
                }
                return this.schema.required.indexOf(this.field.id) >= 0;
            },
            is_bool: function() {
                return this.property && this.property.type === 'boolean';
            },
            value: function() {
                if (this.model && this.field) {
                    return this.model[this.field.id];
                }
                return '';
            },
            placeholder: function() {
                return this.field.placeholder || this.field.label;
            },
            widget: function() {
                if (this.field.widget) {
                    return this.field.widget;
                }
                if (this.property.type === 'string') {
                    if (this.property.format === 'markdown') {
                        return 'markdown-editor';
                    }
                }
                return 'text-input';
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

});
