/*
* Handle authentication and permissions
*/
import $ from 'jquery';
import config from 'config';
import Notify from 'notify';
import i18n from 'i18n';

const DEFAULT_NEED_ROLE = i18n._('Role "{role}" is required', {role: 'ROLE'});


export const user = config.user;

/**
 * Build the authentication URL given the current page and an optionnal message.
 */
export function get_auth_url(message) {
    const params = {next: window.location.href};

    if (message) {
        params.message = message;
    }

    return config.auth_url + '?' + $.param(params);
}

/**
 * Check if an user is authenticated
 */
export function need_user(message) {
    if (!user) {
        window.location = get_auth_url(message);
        return false;
    }
    return true;
}

/**
 * Check that the current authenticated user has a given role.
 */
export function has_role(role) {
    return user && user.roles.indexOf(role) > 0;
}

/**
 * Check that the current authenticated user has a given role.
 * Notify if not.
 */
export function need_role(role, message) {
    need_user();
    if (user.roles.indexOf(role) < 0) {
        const msg = (message || DEFAULT_NEED_ROLE).replace('ROLE', role);
        Notify.error(msg);
    }
}

export default {
    user,
    get_auth_url,
    need_user,
    has_role,
    need_role,
};
