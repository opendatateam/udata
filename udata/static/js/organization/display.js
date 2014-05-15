/**
 * Default JS module
 */
define(['logger', 'widgets/starred', 'widgets/follow-btn'], function(log) {
    return {
        start: function() {
            log.debug('Organization display page');
        }
    }
});
