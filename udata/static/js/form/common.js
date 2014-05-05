/**
 * Common form features
 */
define(['jquery', 'jquery.validation', 'bootstrap' ], function($) {
    'use strict';

    // jQuery validate
    $('form.validation').validate({
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
        }
    });


    // i18n: function(key, replacements) {
    //     var msg = $('meta[name="'+key+'-i18n"]').attr('content');
    //     if (replacements) {
    //         for (var key in replacements) {
    //             msg = msg.replace(key, replacements[key]);
    //         }
    //     }
    //     return msg;
    // },

    // jQuery validate
    // $.extend($.validator.messages, {
    //     required: Utils.i18n('valid-required'),
    //     remote: Utils.i18n('valid-remote'),
    //     email: Utils.i18n('valid-email'),
    //     url: Utils.i18n('valid-url'),
    //     date: Utils.i18n('valid-date'),
    //     dateISO: Utils.i18n('valid-date-iso'),
    //     number: Utils.i18n('valid-number'),
    //     digits: Utils.i18n('valid-digits'),
    //     creditcard: Utils.i18n('valid-creditcard'),
    //     equalTo: Utils.i18n('valid-equal-to'),
    //     maxlength: $.validator.format(Utils.i18n('valid-maxlength')),
    //     minlength: $.validator.format(Utils.i18n('valid-minlength')),
    //     rangelength: $.validator.format(Utils.i18n('valid-range-length')),
    //     range: $.validator.format(Utils.i18n('valid-range')),
    //     max: $.validator.format(Utils.i18n('valid-max')),
    //     min: $.validator.format(Utils.i18n('valid-min'))
    // });

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

});
