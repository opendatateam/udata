/**
 * Common stack, plugins and helpers
 */
define(['jquery'], function($) {
    'use strict';

    function call(method, url, data, callback) {
        return $.ajax({
            'type': method,
            'url': url,
            'contentType': 'application/json',
            'data': JSON.stringify(data||{}),
            'dataType': 'json',
            'success': callback
        });
    }

    var API = {
        get: $.get,
        post: function(url, data, callback) {
            return call('post', url, data, callback);
        },
        put: function(url, data, callback) {
            return call('put', url, data, callback);
        },
        delete: function(url, data, callback) {
            return call('delete', url, data, callback);
        }
    };

    return API;

});
