define(['vue', 'logger', 'jquery', 'jquery-validation'], function(Vue, log, $) {
    'use strict';

    // jQuery validate
    $.extend($.validator.messages, {
        required: Vue._('valid-required'),
        remote: Vue._('valid-remote'),
        email: Vue._('valid-email'),
        url: Vue._('valid-url'),
        date: Vue._('valid-date'),
        dateISO: Vue._('valid-date-iso'),
        number: Vue._('valid-number'),
        digits: Vue._('valid-digits'),
        creditcard: Vue._('valid-creditcard'),
        equalTo: Vue._('valid-equal-to'),
        maxlength: $.validator.format(Vue._('valid-maxlength')),
        minlength: $.validator.format(Vue._('valid-minlength')),
        rangelength: $.validator.format(Vue._('valid-range-length')),
        range: $.validator.format(Vue._('valid-range')),
        max: $.validator.format(Vue._('valid-max')),
        min: $.validator.format(Vue._('valid-min'))
    });

    function empty_schema() {
        return {properties: {}, required: []};
    }

    return {
        name: 'base-form',
        replace: true,
        paramAttributes: ['fields', 'model', 'defs', 'readonly', 'fill'],
        computed: {
            schema: function() {
                if (!this.fields || !(this.model || this.defs)) {
                    return empty_schema();
                }
                var s = empty_schema(),
                    schema = this.defs || this.model.schema || empty_schema();

                this.fields.forEach(function(field) {
                    if (!schema.properties.hasOwnProperty(field.id)) {
                        log.error('Property "'+ field.id +'" not found in schema');
                    }
                    s.properties[field.id] = schema.properties[field.id];
                    if (schema.required.indexOf(field.id) > 0) {
                        s.required.push(field.id);
                    }
                }.bind(this));

                return s;
            },
            form_data: function() {
                return Vue.util.serialize_form(this.$el);
            },
            $form: function() {
                return $(this.$el).is('form') ? $(this.$el) : this.$find('form');
            }
        },
        attached: function() {
            this.$form.validate({
                errorClass: "help-block",
                highlight: function(element) {
                    $(element).closest('.form-group').removeClass('has-success').addClass('has-error');
                },
                unhighlight: function(element) {
                    $(element).closest('.form-group').removeClass('has-error');
                },
                success: function(label) {
                    label.closest('.form-group').addClass('has-success');
                    if (!label.text()) {
                        label.remove();
                    }
                },
                errorPlacement: function(error, element) {
                    $(element).closest('.form-group,.field-wrapper').append(error);
                }
            });
        },
        detached: function() {
            this.$form.data('validator', null);
        },
        methods: {
            validate: function() {
                return this.$form.valid();
            },
            serialize: function() {
                return Vue.util.serialize_form(this.$el);
            }
        }
    };

});
