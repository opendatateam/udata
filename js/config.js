/*
 * Parse the headers to extract some informations
 */

/**
 * The current user extracted from the header
 */
export let user;
const userEl = document.querySelector('meta[name=current-user]');

if (userEl) {
    user = {
        id: userEl.getAttribute('content'),
        slug: userEl.dataset.slug,
        first_name: userEl.dataset.first_name,
        last_name: userEl.dataset.last_name,
        roles: userEl.dataset.roles.split(','),
    };
}

// export user;
export const debug = DEBUG;
export const collapse_width = 992;
export const lang = document.querySelector('html').getAttribute('lang') || 'en';
export const title = document.querySelector('meta[name=site-title]').getAttribute('content');

export const csrf_token = document.querySelector('meta[name=csrf-token]').getAttribute('content');
export const api_root = document.querySelector('link[rel=api-root]').getAttribute('href');
export const api_specs = document.querySelector('link[rel=api-specs]').getAttribute('href');
export const theme_static = document.querySelector('link[rel=theme-static-root]').getAttribute('href');
export const static_root = document.querySelector('link[rel=static-root]').getAttribute('href');
export const admin_root = document.querySelector('link[rel=admin-root]').getAttribute('href');
export const auth_url = document.querySelector('link[rel=auth-url]').getAttribute('href');

export default {
    user,
    debug,
    collapse_width,
    lang,
    title,
    csrf_token,
    api_root,
    api_specs,
    theme_static,
    static_root,
    admin_root,
    auth_url,
};
