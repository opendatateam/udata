/**
 * Default JS module
 */
define(['logger', 'widgets/starred'], function(log) {
    return {
        start: function() {
            log.debug('Organization display page');
        }
    }
});
