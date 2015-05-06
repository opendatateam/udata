define(['logger'], function(log) {
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
            'select-input': require('components/form/select-input.vue'),
            'markdown-editor': require('components/form/markdown.vue'),
            'tag-completer': require('components/form/tag-completer'),
            'dataset-completer': require('components/form/dataset-completer'),
            'reuse-completer': require('components/form/reuse-completer'),
            'license-completer': require('components/form/license-completer'),
            'territory-completer': require('components/form/territory-completer'),
            'zone-completer': require('components/form/zone-completer.vue'),
            'format-completer': require('components/form/format-completer'),
            'checksum': require('components/form/checksum.vue')
        },
        computed: {
            property: function() {
                // console.log('prop', this.field.id, this.schema, this.schema.properties.hasOwnProperty(this.field.id))
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
            field_type: function() {
                var prop = this.property;
                if (!prop) {
                    return;
                }
                if (prop.type === 'string' && prop.format === 'markdown') {
                    return 'markdown';
                };
            },
            is_input: function() {
                return !this.field_type;
            },
            is_bool: function() {
                return this.field_type === 'checkbox' || this.field_type === 'radio';
            },
            value: function() {
                if (this.model && this.field) {
                    return this.model[this.field.id];
                }
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
