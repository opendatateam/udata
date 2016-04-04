import config from 'config';

export function install(Vue) {
    Vue.use(require('vue-resource'));

    if (config.api_root.endsWith('/')) {
        Vue.http.options.root = config.api_root.substring(0, config.api_root.length - 1);
    } else {
        Vue.http.options.root = config.api_root;
    }

    ['post', 'put', 'patch', 'delete'].forEach(method => {
        Vue.http.headers[method]['X-CSRFToken'] = config.csrftoken;
    });

    // Vue.http.interceptors.push({
    //     /**
    //      * Store the sentry ID if available
    //      */
    //     response(response) {
    //         response.sentry_id = response.headers('X-Sentry-ID');
    //         return response;
    //     }
    // });
}
