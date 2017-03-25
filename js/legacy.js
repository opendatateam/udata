/**
 * Common stack, plugins and helpers
 */
import $ from 'jquery';
import 'bootstrap';
import 'utils/ellipsis';
import 'i18n';

$(function() {
    // Display popovers with markup
    $('[data-toggle="popover"]').popover().on('click', function(e) {
        if ($(this).data('trigger').match(/(click|focus)/)) {
            e.preventDefault();
            return true;
        }
    });
});
