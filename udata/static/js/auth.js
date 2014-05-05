/**
 * Authentication and permissions handling
 */
define(['jquery'], function($) {
    'use strict';

    return {
        ensure_user: function(reason) {
            var $sso = $('#sso-link');
            if ($sso.length) {
                var url = $sso.attr('href');
                if (reason) {
                    url += url.indexOf('?') > 0 ? '&' : '?';
                    url += 'message=' + encodeURIComponent(reason);
                }
                window.location = url;
            }
        }
    }

});
