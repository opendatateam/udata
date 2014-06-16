/**
 * Common form features
 */
define(['jquery', 'i18n', 'jquery.validation', 'bootstrap' ], function($, i18n) {
    'use strict';

    var rules = {
        errorClass: "help-block",
        highlight: function(element) {
            console.log(element);
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
        }
    };

    // jQuery validate
    $('form.validation').validate(rules);

    // jQuery validate
    $.extend($.validator.messages, {
        required: i18n._('valid-required'),
        remote: i18n._('valid-remote'),
        email: i18n._('valid-email'),
        url: i18n._('valid-url'),
        date: i18n._('valid-date'),
        dateISO: i18n._('valid-date-iso'),
        number: i18n._('valid-number'),
        digits: i18n._('valid-digits'),
        creditcard: i18n._('valid-creditcard'),
        equalTo: i18n._('valid-equal-to'),
        maxlength: $.validator.format(i18n._('valid-maxlength')),
        minlength: $.validator.format(i18n._('valid-minlength')),
        rangelength: $.validator.format(i18n._('valid-range-length')),
        range: $.validator.format(i18n._('valid-range')),
        max: $.validator.format(i18n._('valid-max')),
        min: $.validator.format(i18n._('valid-min'))
    });

    // Form help messages as popover on info sign
    $('.form-help').popover({
        placement: 'top',
        trigger: 'hover',
        container: 'body',
        html: true
    });

    // Transform some links into postable forms
    $('a.postable').click(function() {
        var $a = $(this);

        $('<form/>', {method: 'post', action: $a.attr('href')})
            .append($('<input/>', {name: $a.data('field-name'), value: $a.data('field-value')}))
            .append($('<input/>', {name: 'csrfmiddlewaretoken', value: $.cookie('csrftoken')}))
            .appendTo('body')
            .submit();

        return false;
    });


    // Publisher card handling
    $('.publisher-card, .publisher-card a').click(function() {
        var $card = $(this).closest('.publisher-card'),
            $input = $card.closest('.form-group').find('input[type="hidden"]'),
            org_id = $card.data('org-id');

        $(this).closest('.card-list').find('.publisher-card').removeClass('active');
        $card.addClass('active');

        $input.val(org_id);

        return false;
    });

    return {
        rules: rules
    };

});
