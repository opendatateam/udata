import $ from 'jquery';
import SwaggerClient from 'swagger-client';
import config from 'config';
import log from 'logger';


function updateQueryParam(uri, key, value) {
    const re = new RegExp(`([?&])${key}=.*?(&|$)`, 'i');
    const separator = uri.indexOf('?') !== -1 ? '&' : '?';
    if (uri.match(re)) {
        return uri.replace(re, `$1${key}=${value}$2`);
    } else {
        return `${uri}${separator}${key}=${value}`;
    }
}

/**
 * This object inject the lang query parameter in every API request
 */
const LangParameter = function(name) {
  this.name = name;
};

LangParameter.prototype.apply = function(obj) {
    obj.url = updateQueryParam(obj.url, 'lang', config.lang);
    return true;
};


const API = new SwaggerClient({
    debug: config.debug,
    url: config.api_specs,
    useJQuery: true,
    success: function() {
        $(this).trigger('built');
    },
    progress: function(msg) {
        log.debug(msg);
    },
    authorizations: {
        lang: new LangParameter()
    }
});

/**
 * Resolve a definition from a $ref
 * @param  {String} $ref The reference string
 * @return {Object}      The resolved schema
 */
API.resolve = function($ref) {
    const def = $ref.replace(config.api_specs, '').replace('#/definitions/', '');
    return this.definitions[def];
};

export default API;
