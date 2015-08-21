define([
    'jquery',
    'swagger-client',
    'config',
    'logger'
], function($, SwaggerClient, config, log) {
    'use strict';

    var API = new SwaggerClient({
        debug: config.debug,
        url: config.api,
        useJQuery: true,
        success: function() {
            $(this).trigger('built');
        },
        progress: function(msg) {
            log.debug(msg);
        }
    });

    return API;
});
