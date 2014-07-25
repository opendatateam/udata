/**
 * Dataset form
 */
define([
    'logger',
    'form/widgets',
    'form/format-completer',
    'form/upload'
], function(log) {
    return {
        start: function() {
            log.debug('Resource form loaded');
        }
    }
});
