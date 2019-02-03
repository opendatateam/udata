import API from 'api';
import {_} from 'i18n';
import {setattr, isObject, isString, findComponent} from 'utils';
import log from 'logger';
import moment from 'moment';
import $ from 'jquery-validation';  // Ensure jquery & jquery.validate plugin are both loaded

// Remove warning for non-interpolated variables
const interpolation = {defaultVariables: {'O': '{O}', '1': '{1}', 'ISO': '{ISO}'}};

// jQuery validate
$.extend($.validator.messages, {
    required: _('valid-required'),
    remote: _('valid-remote'),
    email: _('valid-email'),
    url: _('valid-url'),
    date: _('valid-date'),
    dateISO: _('valid-date-iso', {interpolation: interpolation}),
    number: _('valid-number'),
    digits: _('valid-digits'),
    creditcard: _('valid-creditcard'),
    equalTo: _('valid-equal-to'),
    maxlength: $.validator.format(_('valid-maxlength', {interpolation: interpolation})),
    minlength: $.validator.format(_('valid-minlength', {interpolation: interpolation})),
    rangelength: $.validator.format(_('valid-range-length', {interpolation: interpolation})),
    range: $.validator.format(_('valid-range', {interpolation: interpolation})),
    max: $.validator.format(_('valid-max', {interpolation: interpolation})),
    min: $.validator.format(_('valid-min', {interpolation: interpolation}))
});


/**
 *  Rule for depend dates, should be greater that param.
 */
$.validator.addMethod('dateGreaterThan', function(value, element, param) {
    const start = moment(document.getElementById(param).value);
    return this.optional(element) || moment(value).isAfter(start);
}, $.validator.format(_('Date should be after start date')));


function empty_schema() {
    return {properties: {}, required: []};
}

/**
 * Input type which are text or formated text
 *
 * See: https://www.w3.org/TR/html5/forms.html#attr-input-type
 */
const TEXT_INPUTS = [
    'color',
    'date',
    'datetime',
    'datetime-local',
    'email',
    'hidden',
    'month',
    'number',
    'range',
    'search',
    'tel',
    'text',
    'time',
    'url',
    'week',
];

/**
 * Form tags that should be considered as text
 */
const TEXT_TAGS = ['select', 'textarea'];

export default {
    name: 'base-form',
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
    events: {
        'field:change': function(field, value) {
            this.$dispatch('form:change', this, field, value);
            return true;  // Let the event continue its bubbling
        }
    },
    computed: {
        schema() {
            if (!this.fields || !(this.model || this.defs)) {
                return empty_schema();
            }
            const s = empty_schema();
            const schema = this.defs || this.model && this.model.__schema__ || empty_schema();

            this.fields.forEach((field) => {
                if (schema.hasOwnProperty('properties') && schema.properties.hasOwnProperty(field.id)) {
                    s.properties[field.id] = schema.properties[field.id];
                    if (schema.required && schema.required.indexOf(field.id) >= 0) {
                        s.required.push(field.id);
                    }
                    return;
                }

                const properties = field.id.split('.');
                let currentSchema = schema;
                let required = true;
                let path = '';
                let prop;

                for (prop of properties) {
                    path += path === '' ? prop : ('.' + prop);

                    // Handle root level $ref
                    if (currentSchema.hasOwnProperty('$ref')) {
                        currentSchema = API.resolve(currentSchema.$ref);
                    }

                    if (!currentSchema.properties || !currentSchema.properties.hasOwnProperty(prop)) {
                        log.warn(`Property "${prop}" not found in schema`);
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
        $form() {
            if (!this) return;  // Prevent console noise on a non significant error
            return this.$refs.form || this.$els.form || this.$el;
        }
    },
    attached() {
        $(this.$form).validate({
            ignore: '',
            errorClass: 'help-block',
            highlight: this.highlight,
            unhighlight: this.unhighlight,
            success: this.success,
            showErrors: this.showErrors,
            errorPlacement() {},
        });
        this.$broadcast('form:ready');
    },
    beforeDestroy() {
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
        validate() {
            return $(this.$form).valid();
        },
        /**
         * Serialize Form into an Object
         *
         * @return {Object}
         */
        serialize() {
            const elements = this.$form.querySelectorAll('input,textarea,select');
            const out = {};

            Array.prototype.map.call(elements, function(el) {
                let value;
                if (el.tagName.toLowerCase() === 'select' && el.multiple) {
                    value = [...el.options]
                    value = value.filter(option => option.selected)
                    value = value.map(option => option.value)
                } else if (TEXT_TAGS.includes(el.tagName.toLowerCase()) || TEXT_INPUTS.includes(el.type.toLowerCase())) {
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

            // Filter out empty optional objects
            // TODO: handle recursion
            for (const prop in out) {
                if (isObject(out[prop]) && this.schema.required.indexOf(prop) < 0) {
                    let falsy = true;
                    for (const attr in out[prop]) {
                        if (out[prop].hasOwnProperty(attr)) {
                            falsy &= !out[prop][attr];
                        }
                    }
                    if (falsy) {
                        delete out[prop];
                    }
                }
            }

            return out;
        },
        on_error(response) {
            const messages = [];

            // Errors occuring before submission are simple strings
            if (isString(response)) {
                log.error(response);  // Technical and non translatable, logged for better handling later
                // TODO: Optional Sentry handling
                return;
            }

            // Display the error identifier if present
            if (response.headers && 'X-Sentry-ID' in response.headers) {
                messages.push(
                    this._('The error identifier is {id}', {id: response.headers['X-Sentry-ID']})
                );
            }

            if ('data' in response) {
                let data = {};
                try {
                    data = JSON.parse(response.data);
                } catch (e) {
                    log.warn('Parsing error:', e);
                    // TODO: Optional Sentry handling
                }

                if ('errors' in data) {
                    this.fill_errors(data.errors);
                    return;  // Form errors does not need to be notified
                } else if ('message' in data) {
                    messages.push(data.message);
                }
            }

            if (!messages.length) {
                messages.push(this._('An unkown error occured'));
            }

            this.$dispatch('notify', {
                type: 'error',
                icon: 'exclamation-triangle',
                title: this._('An error occured'),
                details: messages.join('\n'),
            });
        },
        fill_errors(errors) {
            Object.entries(errors).forEach(([field, errs]) => {
                const el = this.$form.querySelector(`[name="${field}"]`);
                const $field = this.findField(el);
                $field.errors = errs;
                $field.success = false;
            });
        },
        highlight(element) {
            this.findField(element).success = false;
        },
        unhighlight(element) {
            this.findField(element).errors = [];
        },
        /**
         * Inject jQuery.Validation errors into their fields
         *
         * See: https://jqueryvalidation.org/category/plugin/#showerrors
         */
        showErrors(errorMap, errorList) {
            errorList.forEach(error => {
                this.findField(error.element).errors = [error.message];
            });
            $(this.$form).data('validator').defaultShowErrors();
        },
        /**
         * Mark a field as `success`
         */
        success(label, el) {
            this.findField(el).success = true;
        },
        /**
         * Find the form field containing a given DOM field
         *
         * @param {Element} el The DOM element to match
         */
        findField(el) {
            let $component = findComponent(this, el);
            while (!$component.isField) {
                $component = $component.$parent;
            }
            return $component;
        }
    }
};
