/**
 * Default JS module
 */
define([
    'logger',
    'widgets/featured',
    'widgets/follow-btn',
    'widgets/issues-btn'
], function(log) {
    return {
        start: function() {
            log.debug('Reuse display page');
        }
    }
});
