/**
 * Authentication and permissions handling
 */
define(['jquery', 'notify', 'i18n', 'class'], function($, Notify, i18n, Class) {
    'use strict';

    var DEFAULTS = {
        need_role: i18n._('Role "{role}" is required')
    }


    var Auth = Class.extend({
        /**
         * Store the current user if logged.
         */
        user: undefined,

        /**
         * Fetch the needed data from the page.
         */
        init: function() {

            var $el = $('meta[name=current-user]');

            if ($el.length) {
                this.user = {
                    id: $el.attr('content'),
                    slug: $el.data('slug'),
                    first_name: $el.data('first_name'),
                    last_name: $el.data('last_name'),
                    roles: $el.data('roles').split(',')
                }
            }

            this.auth_url = $('meta[name=auth-url]').attr('content');

        },

        /**
         * Build the authentication URL given the current page and an optionnal message.
         */
        get_auth_url: function(message) {
            var params = {next: window.location.href};

            if (message) {
                params.message = message
            }

            return this.auth_url + '?' + $.param(params);
        },

        /**
         * Check if an user is authenticated
         */
        need_user: function(message) {
            if (!this.user) {
                window.location = this.get_auth_url(message)
                return false;
            }
            return true;
        },

        /**
         * Check that the current authenticated user has a given role.
         */
        has_role: function(role) {
            return this.user && this.user.roles.indexOf(role) > 0;
        },

        /**
         * Check that the current authenticated user has a given role.
         * Notify if not.
         */
        need_role: function(role, message) {
            this.need_user();
            if (this.user.roles.indexOf(role) < 0) {
                var msg = (message || DEFAULTS.need_role).replace('{role}', role);
                Notify.error(msg);
            }
        }

    });

    return new Auth();

});
