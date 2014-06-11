/**
 * Default JS module
 */
define(['logger', 'widgets/featured', 'widgets/follow-btn'], function(log) {
    return {
        start: function() {
            log.debug('Reuse display page');
        }
    }
});
