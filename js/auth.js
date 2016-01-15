import $ from 'jquery';
import Notify from 'notify';
import i18n from 'i18n';

const DEFAULTS = {
    need_role: i18n._('Role "{role}" is required')
};


/**
 * Handle authentication and permissions
 */
class Auth {
    /**
     * Fetch the needed data from the page.
     */
    constructor() {
        const $el = $('meta[name=current-user]');

        if ($el.length) {
            this.user = {
                id: $el.attr('content'),
                slug: $el.data('slug'),
                first_name: $el.data('first_name'),
                last_name: $el.data('last_name'),
                roles: $el.data('roles').split(',')
            };
        }

        this.auth_url = $('meta[name=auth-url]').attr('content');
    }

    /**
     * Build the authentication URL given the current page and an optionnal message.
     */
    get_auth_url(message) {
        const params = {next: window.location.href};

        if (message) {
            params.message = message;
        }

        return this.auth_url + '?' + $.param(params);
    }

    /**
     * Check if an user is authenticated
     */
    need_user(message) {
        if (!this.user) {
            window.location = this.get_auth_url(message);
            return false;
        }
        return true;
    }

    /**
     * Check that the current authenticated user has a given role.
     */
    has_role(role) {
        return this.user && this.user.roles.indexOf(role) > 0;
    }

    /**
     * Check that the current authenticated user has a given role.
     * Notify if not.
     */
    need_role(role, message) {
        this.need_user();
        if (this.user.roles.indexOf(role) < 0) {
            const msg = (message || DEFAULTS.need_role).replace('{role}', role);
            Notify.error(msg);
        }
    }
}


export default new Auth();
