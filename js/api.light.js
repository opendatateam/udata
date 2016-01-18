/**
 * Common stack, plugins and helpers
 */
define(['jquery', 'config'], function($, config) {
    'use strict';

    var API_ROOT = config.api_root;

    if (API_ROOT[API_ROOT.length - 1] == '/') {
        // Remove trailing slash
        API_ROOT = API_ROOT.substr(0, API_ROOT.length - 1);
    }

    function build_url(url) {
        if (url.substring(0, 4) == 'http') {
            // Absolute url
            return url;
        } else {
            var path = url[0] === '/' ? url: '/' + url,
                api_url;

            if (path.substring(0, API_ROOT.length) == API_ROOT) {
                api_url = path;
            } else {
                api_url = API_ROOT + path;
            }
            return api_url;
        }
    }

    function call(method, url, data, callback) {
        if (method.toLowerCase() != 'get') {
            data = JSON.stringify(data||{});
        }

        return $.ajax({
            type: method,
            url: build_url(url),
            contentType: 'application/json',
            data: data,
            dataType: 'json',
            success: callback
        });
    }

    function synchronous_call(method, url, data) {
        var result,
            options = {
                type: method,
                url: build_url(url),
                contentType: 'application/json',
                dataType: 'json',
                async: false,
                success: function(data) {
                    result = data;
                }
            };

        if (method.toLowerCase() != 'get') {
            options.data = JSON.stringify(data||{});
        } else {
            options.data = data;
        }
        $.ajax(options);
        return result;
    }

    var API = {
        root: API_ROOT,
        build_url: build_url,
        get: function(url, data, callback) {
            if (callback) {
                return call('get', url, data, callback);
            } else {
                return call('get', url, null, data);
            }
        },
        post: function(url, data, callback) {
            return call('post', url, data, callback);
        },
        put: function(url, data, callback) {
            return call('put', url, data, callback);
        },
        'delete': function(url, data, callback) {
            return call('delete', url, data, callback);
        },
        refs: function(url, callback) {
            if (callback) {
                return call('get', '/references/' + url, null, callback);
            } else {
                return call('get', url);
            }
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
            'delete': function(url, data) {
                return synchronous_call('delete', url, data);
            }
        }
    };

    return API;

});
