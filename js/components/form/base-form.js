import config from 'config';
import API from 'api';
import {_} from 'i18n';
import {setattr, isObject} from 'utils';
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
                    path = '',
                    prop;

                for (prop of properties) {
                    path += path === '' ? prop : ('.' + prop);

                    // Handle root level $ref
                    if (currentSchema.hasOwnProperty('$ref')) {
                        currentSchema = API.resolve(currentSchema.$ref);
                    }

                    if (!currentSchema.properties || !currentSchema.properties.hasOwnProperty(prop)) {
                        log.warn('Property "'+ prop +'" not found in schema');
                        return;
                    }

                    required = (
                        required
                        && currentSchema.hasOwnProperty('required')
                        && currentSchema.required.indexOf(prop) >= 0
                    );

                    if (required && s.required.indexOf(path) < 0) {
                        s.required.push(path);
                    }

                    // Handle property level $ref
                    if (currentSchema.properties[prop].hasOwnProperty('$ref')) {
                        currentSchema = API.resolve(currentSchema.properties[prop].$ref);
                    }
                }

                s.properties[field.id] = currentSchema.properties[prop];
                if (required && !field.id in s.required) {
                    s.required.push(field.id);
                }
            });

            return s;
        },
        $form: function() {
            return this.$refs.form || this.$els.form;
        }
    },
    attached: function() {
        $(this.$form).validate({
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
                $(element).closest('.form-group,.field-wrapper').children('div').append(error);
            }
        });
        this.$broadcast('form:ready');
    },
    beforeDestroy: function() {
        if (this.$form) {
            this.$broadcast('form:beforeDestroy');
            $(this.$form).data('validator', null);
            this.$broadcast('form:destroy');
        }
    },
    methods: {
        /**
         * Trigger a form validation
         */
        validate: function() {
            return $(this.$form).valid();
        },
        /**
         * Serialize Form into an Object
         *
         * @return {Object}
         */
        serialize: function() {
            let elements = this.$form.querySelectorAll('input,textarea,select'),
                out = {};

            Array.prototype.map.call(elements, function(el) {
                let value;
                if (el.tagName.toLowerCase() === 'select') {
                    value = el.value || undefined;
                } else if (el.type === 'checkbox') {
                    value = el.checked;
                } else {
                    value = el.value;
                }
                return {name: el.name, value: value};
            }).forEach(function(item) {
                setattr(out, item.name, item.value);
            });

            // Filter out empty optionnal objects
            // TODO: handle recursion
            for (let prop in out) {
                if (isObject(out[prop]) && this.schema.required.indexOf(prop) < 0) {
                    let falsy = true;
                    for (let attr in out[prop]) {
                        falsy &= !out[prop][attr];
                    }
                    if (falsy) {
                        delete out[prop];
                    }
                }
            }

            return out;
        },
        on_error: function (response) {
            if ('data' in response) {
                let data = {};
                try {
                    data = JSON.parse(response.data);
                } catch (e) {
                    log.warn('Parsing error:', e);
                    return;
                }
                if ('errors' in data) {
                    this.fill_errors(data.errors);
                } else {
                    $(this.$form).append(this.error_element('', data.message));
                }
            }
        },
        fill_errors: function(errors) {
            [...this.$form.querySelectorAll('input,textarea,select')].forEach((element) => {
                if (element.name in errors) {
                    let name = element.name;
                    let error = errors[name][0];
                    $(element).closest('.form-group,.field-wrapper')
                              .removeClass('has-success')
                              .addClass('has-error')
                              .append(this.error_element(name, error));
                }
            });
        },
        error_element: function(id, message) {
            $(`#form-${id}-error`).remove();
            return `<p class="form-error" id="form-${id}-error">${message}</p>`;
        }
    }
};
