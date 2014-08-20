/**
 * Common stack, plugins and helpers
 */
define(['jquery'], function($) {
    'use strict';

    function call(method, url, data, callback) {
        return $.ajax({
            type: method,
            url: url,
            contentType: 'application/json',
            data: JSON.stringify(data||{}),
            dataType: 'json',
            success: callback
        });
    }

    function synchronous_call(method, url, data) {
        var result,
            options = {
                type: method,
                url: url,
                contentType: 'application/json',
                dataType: 'json',
                async: false,
                success: function(data) {
                    result = data
                }
            };
        if (data) {
            options.data = JSON.stringify(data);
        }
        $.ajax(options);
        return result;
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
        },
        sync: {
            get: function(url, data) {
                return synchronous_call('get', url, data);
            },
            post: function(url, data) {
                return synchronous_call('post', url, data);
            },
            put: function(url, data) {
                return synchronous_call('put', url, data);
            },
            delete: function(url, data) {
                return synchronous_call('delete', url, data);
            }
        }
    };

    return API;

});
