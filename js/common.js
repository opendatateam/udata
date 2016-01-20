/**
 * Common stack, plugins and helpers
 */
import config from 'config';
import $ from 'jquery';
import Notify from 'notify';
import 'bootstrap';
import 'widgets/site-search';
import 'utils/ellipsis';
import 'vendor/jquery.microdata';
import 'i18n';

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader('X-CSRFToken', config.csrftoken);
        }
    }
});

$(document).ajaxError(function(event, jqxhr, settings, thrownError) {
    const sentry_id = jqxhr.getResponseHeader('X-Sentry-ID');
    if (sentry_id) {
        Notify.error([
            i18n._('An error occured'),
            i18n._('The error identifier is {id}', {id: sentry_id}),
        ].join('. '))
    }
});

$(function() {
    // Display tooltips and popovers with markup
    $('[rel=tooltip]').tooltip();
    $('[rel=popover]').popover().on('click', function(e) {
        if ($(this).data('trigger').match(/(click|focus)/)) {
            e.preventDefault();
            return true;
        }
    });
});
