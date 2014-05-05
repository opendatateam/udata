/**
 * Homepage specific features
 */
define(['logger', 'jquery'], function(Logger, $) {
    return {
        start: function() {
            $('.carousel').carousel({
                interval: 5000
            });
            Logger.debug('Home page started');
        }
    };
});
