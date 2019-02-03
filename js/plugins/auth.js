/*
* Handle authentication and permissions
*/
import config from 'config';
import CustomError from 'error';
import i18n from 'i18n';

const DEFAULT_NEED_ROLE = i18n._('Role "{role}" is required', {role: 'ROLE'});

export class AuthenticationRequired extends CustomError {}

/**
 * Build the authentication URL given the current page and an optional message.
 */
export function get_auth_url(message) {
    const params = {next: window.location.href};

    if (message) {
        params.message = message;
    }

    return config.auth_url + '?' + Object.keys(params)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
}


export function install(Vue) {
    /**
     * Expose the current user
     */
    Vue.prototype.$user = config.user;

    /**
     * Checks if the current user is authenticated
     * and triggers a login if it's not the case.
     *
     * The current function execution is stopped by
     * raising a AuthenticationRequired error.
     *
     * @param  {String} message The contextual message to display on login screen
     * @throws  {AuthenticationRequired} When the user is not authentified
     */
    Vue.prototype.$auth = function(message) {
        if (!this.$user) {
            window.location = get_auth_url(message);
            throw new AuthenticationRequired(message);  // This avoid calling function to continue its execution
        }
    };

    /**
     * Check that the current authenticated user has a given role.
     * Notify if not.
     */
    Vue.prototype.$role = function(role, message) {
        this.$auth();
        if (this.$user.roles.indexOf(role) < 0) {
            const msg = (message || DEFAULT_NEED_ROLE).replace('ROLE', role);
            this.$dispatch('notify:error', msg);
        }
    };
}
