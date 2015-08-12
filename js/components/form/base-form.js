import config from 'config';
import API from 'api';
import {_} from 'i18n';
import {setattr} from 'utils';
import log from 'logger';
import moment from 'moment';
import $ from 'jquery'
import 'jquery-validation-dist';

// jQuery validate
$.extend($.validator.messages, {
    required: _('valid-required'),
    remote: _('valid-remote'),
    email: _('valid-email'),
    url: _('valid-url'),
    date: _('valid-date'),
    dateISO: _('valid-date-iso'),
    number: _('valid-number'),
    digits: _('valid-digits'),
    creditcard: _('valid-creditcard'),
    equalTo: _('valid-equal-to'),
    maxlength: $.validator.format(_('valid-maxlength')),
    minlength: $.validator.format(_('valid-minlength')),
    rangelength: $.validator.format(_('valid-range-length')),
    range: $.validator.format(_('valid-range')),
    max: $.validator.format(_('valid-max')),
    min: $.validator.format(_('valid-min'))
});


/**
 *  Rule for depend dates, should be greater that param.
 */
$.validator.addMethod('dateGreaterThan', function(value, element, param) {
    var start = moment($(param).val());
    return this.optional(element) || moment(value).isAfter(start);
}, $.validator.format(_('Date should be after start date')));


function empty_schema() {
    return {properties: {}, required: []};
}


export default {
    name: 'base-form',
    replace: true,
    props: {
        fields: Array,
        model: Object,
        defs: Object,
        readonly: {
            type: Boolean,
            default: false
        },
        fill: Boolean
    },
    computed: {
        schema: function() {
            if (!this.fields || !(this.model || this.defs)) {
                return empty_schema();
            }
            var s = empty_schema(),
                schema = this.defs || this.model.__schema__ || empty_schema();

            this.fields.forEach((field) => {
                if (schema.hasOwnProperty('properties') && schema.properties.hasOwnProperty(field.id)) {
                    s.properties[field.id] = schema.properties[field.id];
                    if (schema.required && schema.required.indexOf(field.id) >= 0) {
                        s.required.push(field.id);
                    }
                    return;
                }

                let properties = field.id.split('.'),
                    currentSchema = schema,
                    required = true,
                    prop;

                for (prop of properties) {
                    // Handle root level $ref
                    if (currentSchema.hasOwnProperty('$ref')) {
                        let def = currentSchema.$ref.replace('#/definitions/', '');
                        currentSchema = API.definitions[def];
                    }

                    if (!currentSchema.properties || !currentSchema.properties.hasOwnProperty(prop)) {
                        log.warn('Property "'+ prop +'" not found in schema');
                        return;
                    }

                    required &= currentSchema.required && currentSchema.required.indexOf(prop) >= 0;

                    // Handle property level $ref
                    if (currentSchema.properties[prop].hasOwnProperty('$ref')) {
                        let def = currentSchema.properties[prop].$ref.replace('#/definitions/', '');
                        currentSchema = API.definitions[def];
                    }
                }

                s.properties[field.id] = currentSchema.properties[prop];
                if (required) {
                    s.required.push(field.id);
                }
            });

            return s;
        },
        $form: function() {
            return $(this.$el).is('form') ? $(this.$el) : this.$find('form');
        }
    },
    attached: function() {
        this.$form.validate({
            ignore: '',
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
        /**
         * Serialize Form into an Object following the W3C specs:
         * http://www.w3.org/TR/html-json-forms/
         *
         * @return {Object}
         */
        serialize: function() {
            let array = this.$form.serializeArray(),
                json = {};

            array.forEach((item) => {
                if (item.value) {
                    if ((item.name) in this.schema.properties
                        && 'type' in this.schema.properties[item.name]
                        && this.schema.properties[item.name].type ==='boolean')
                    {
                        setattr(json, item.name, true);
                    } else {
                        setattr(json, item.name, item.value);
                    }
                }
            });

            return json;
        }
    }
};
