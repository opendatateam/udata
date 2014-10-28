/**
 * Common stack, plugins and helpers
 */
define([
    'jquery',
    'auth',
    'bootstrap',
    'widgets/site-search',
    'utils/ellipsis',
    'jquery.microdata',
    'i18n'
], function($) {

    var csrftoken = $('meta[name=csrf-token]').attr('content');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        }
    })

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
});
