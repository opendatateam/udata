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

    /**
     * Resolve a definition from a $ref
     * @param  {String} $ref The reference string
     * @return {Object}      The resolved schema
     */
    API.resolve = function($ref) {
        let def = $ref.replace(config.api, '').replace('#/definitions/', '');
        return this.definitions[def];
    };

    return API;
});
