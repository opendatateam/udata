/**
 * Featured button
 */
define(['jquery', 'bootstrap-slider'], function($) {
    'use strict';

    // Search range picker
    $('input.range-picker').each(function() {
        $(this).slider({}).on('slideStop', function() {
            var value = $(this).slider('getValue').join('-');
            window.location = $(this).data('url-pattern').replace('__r__', value);
        });
    });
});
