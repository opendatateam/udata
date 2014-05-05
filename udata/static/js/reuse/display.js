/**
 * Default JS module
 */
define(['logger', 'widgets/featured', 'widgets/starred'], function(log) {
    return {
        start: function() {
            log.debug('Reuse display page');
        }
    }
});
