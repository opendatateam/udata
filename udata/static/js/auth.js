/**
 * Authentication and permissions handling
 */
define(['jquery'], function($) {
    'use strict';

    var $el = $('meta[name=current-user]'),
        auth_url = $('meta[name=auth-url]').attr('content'),
        user;

    if ($el.length) {
        user = {
            id: $el.attr('content'),
            slug: $el.data('slug'),
            first_name: $el.data('first_name'),
            last_name: $el.data('last_name'),
            roles: $el.data('roles').split(',')
        }
    }

    /**
     * Build the authentication URL given the current page and an optionnal message.
     */
    function get_auth_url(message) {
        var params = {next: window.location.href};

        if (message) {
            params.message = message
        }

        return auth_url + '?' + $.param(params);
    }

    return {
        user: user,
        ensure_user: function(reason) {
            if (!user) {
                window.location = get_auth_url(reason)
            }
        }
    }

});
