/**
 * Homepage specific features
 */
define(['logger', 'jquery'], function(Logger, $) {
    return {
        start: function() {
            $('.carousel').carousel();
            Logger.debug('Home page started');
        }
    };
});
