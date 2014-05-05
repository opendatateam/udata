/**
 * Default JS module
 */
define(['logger', 'widgets/featured', 'widgets/starred'], function(log) {
    return {
        start: function() {
            log.debug('Dataset display page');
        }
    }
});
