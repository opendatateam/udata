/**
 * Default JS module
 */
define([
    'jquery',
    'logger',
    'widgets/starred',
    'widgets/follow-btn'
], function($, log) {
    return {
        start: function() {
            log.debug('Organization display page');

            // Link tabs and history
            if (location.hash !== '') {
                $('a[href="' + location.hash + '"]').tab('show');
            }
            $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
                return location.hash = $(e.target).attr('href').substr(1);
            });
        }
    }
});
