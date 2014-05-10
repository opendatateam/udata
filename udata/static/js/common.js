/**
 * Common stack, plugins and helpers
 */
define([
    'jquery', 'bootstrap', 'widgets/site-search', 'utils/ellipsis', 'i18n'
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
        $('[rel=popover]').popover();
    });
});
