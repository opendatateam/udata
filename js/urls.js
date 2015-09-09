/**
 * Build external URLs
 */
define(['jquery'], function($) {
    'use strict';

    var URLS = {
        'organization.datasets_csv': '/organizations/{org}/datasets.csv',
        'organization.datasets_resources_csv': '/organizations/{org}/datasets-resources.csv',
        'organizations.show': '/organizations/{org}/',
        'users.show': '/users/{user}/'
    };

    function UrlBuildError(msg) {
        this.msg = msg;
    }

    /**
     * Replace objects by their ID if present
     */
    function urlize(obj) {
        if (obj && obj instanceof Object) {
            // Gives priority to slug, might be fragile.
            if (obj.hasOwnProperty('slug')) {
                return obj.slug;
            } else if (obj.hasOwnProperty('id')) {
                return obj.id;
            }
        }
        return obj;
    }

    return {
        build: function(endpoint, options) {
            if (!URLS.hasOwnProperty(endpoint)) {
                throw new UrlBuildError('Endpoint "' + endpoint + '" not found');
            }
            var url = URLS[endpoint],
                args = {};
            for (var name in options) {
                if (options.hasOwnProperty(name)) {
                    var token = '{' + name + '}',
                        value = urlize(options[name]);

                    if (url.indexOf(token) >= 0) {
                        url = url.replace(token, value);
                    } else {
                        args[name] = value;
                    }
                }
            }
            if (args && args.length > 0) {
                url += '?' + $.param(args);
            }
            return url;
        }
    };
});
