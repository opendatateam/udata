/**
 * Dataset form
 */
define([
    'logger',
    'form/common',
    'form/markdown',
    'form/format-completer',
    'form/upload'
], function(log) {
    return {
        start: function() {
            log.debug('Resource form loaded');
        }
    }
});
