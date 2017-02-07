/**
 * Common form features
 */
define(['jquery', 'i18n', 'jquery-validation-dist', 'bootstrap' ], function($, i18n) {
    'use strict';

    var csrftoken = $('meta[name=csrf-token]').attr('content'),
        rules = {
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
        };

    function build(url) {
        return $('<form/>', {method: 'post', action: url})
            .append($('<input/>').attr({name: 'csrf_token', value: csrftoken}))
            .appendTo('body');
    }

    // jQuery validate
    $('form.validation').validate(rules);

    const interpolation = {defaultVariables: {'O': '{O}', '1': '{1}', 'ISO': '{ISO}'}};

    // jQuery validate
    $.extend($.validator.messages, {
        required: i18n._('valid-required'),
        remote: i18n._('valid-remote'),
        email: i18n._('valid-email'),
        url: i18n._('valid-url'),
        date: i18n._('valid-date'),
        dateISO: i18n._('valid-date-iso', {interpolation: interpolation}),
        number: i18n._('valid-number'),
        digits: i18n._('valid-digits'),
        creditcard: i18n._('valid-creditcard'),
        equalTo: i18n._('valid-equal-to'),
        maxlength: $.validator.format(i18n._('valid-maxlength', {interpolation: interpolation})),
        minlength: $.validator.format(i18n._('valid-minlength', {interpolation: interpolation})),
        rangelength: $.validator.format(i18n._('valid-range-length', {interpolation: interpolation})),
        range: $.validator.format(i18n._('valid-range', {interpolation: interpolation})),
        max: $.validator.format(i18n._('valid-max', {interpolation: interpolation})),
        min: $.validator.format(i18n._('valid-min', {interpolation: interpolation}))
    });

    // Form help messages as popover on info sign
    $('.form-help').popover({
        placement: 'top',
        trigger: 'hover',
        container: 'body',
        html: true
    });

    function handle_postables(selector) {
        $(selector).click(function() {
            var $a = $(this);

            build($a.attr('href'))
                .append($('<input/>').attr({name: $a.data('field-name'), value: $a.data('field-value')}))
                .submit();

            return false;
        });
    }

    // Transform some links into postable forms
    handle_postables('a.postable');

    return {
        rules: rules,
        build: build,
        csrftoken: csrftoken,
        handle_postables: handle_postables
    };

});
