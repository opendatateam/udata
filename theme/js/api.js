import $ from 'jquery';
import SwaggerClient from 'swagger-client';
import config from 'config';
import log from 'logger';

/**
 * Update a query string parameter in an URL.
 *
 * If the parameter exists, it is replaced.
 * If not, it is added.
 *
 * @param  {String} uri   The original URL to transform
 * @param  {String} key   The query string parameter name to update
 * @param  {String} value The query string parameter value to set
 * @return {String}       The updated URL
 */
function updateQueryParam(uri, key, value) {
    if (!uri || !key) return;
    // Match an existing key/value pair
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
    success() {
        this.readyCallbacks.forEach(callback => {
            callback(this);
        });
    },
    progress(msg) {
        log.debug(msg);
    },
    authorizations: {
        lang: new LangParameter()
    }
});

API.readyCallbacks = [];

/**
 * Resolve a definition from a $ref
 * @param  {String} $ref The reference string
 * @return {Object}      The resolved schema
 */
API.resolve = function($ref) {
    const def = $ref.split('#')[1].replace('/definitions/', '');
    return this.definitions[def];
};

/**
 * Register a callback to be called when API is ready.
 * The callback should have the following signature: function(API)
 * @param  {Function} callback A callback to call when API is ready.
 */
API.onReady = function(callback) {
    if (this.ready && this.isBuilt) {
        // API is already ready, call the callback immediately
        callback(this);
    } else {
        // Register the callback for later call
        this.readyCallbacks.push(callback);
    }
};

export default API;
