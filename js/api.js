import $ from 'jquery';
import SwaggerClient from 'swagger-client';
import config from 'config';
import log from 'logger';

const API = new SwaggerClient({
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
    const def = $ref.replace(config.api, '').replace('#/definitions/', '');
    return this.definitions[def];
};

export default API;
