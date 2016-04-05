import config from 'config';

export function install(Vue) {

    /**
     * Expect JSON by default
     */
    const DEFAULT_HEADERS = {'Accept': 'application/json'};

    /**
     * Write operations need some extras headers:
     * Send JSON by default and give the x-csrf token
     *
     * Credtentials might be needed here but sessions is used
     */
    const WRITE_HEADERS = {
        'Content-Type': 'application/json',
        'X-CSRFToken': config.csrftoken,
    };


    class Api {
        constructor() {
            this.ROOT = config.api_root.endsWith('/')
                ? config.api_root.substring(0, config.api_root.length - 1)
                : config.api_root;

            // For reusability
            this.DEFAULT_HEADERS = DEFAULT_HEADERS;
            this.WRITE_HEADERS = WRITE_HEADERS;
        }

        /**
         * Tells wether or not a given URL is absolute.
         * @param  {String}  url The URL to test
         * @return {Boolean}     True is the URL is absolute
         */
        isAbsolute(url) {
            return /^https?:\/\//.test(url) || url.startsWith('/');
        }

        /**
         * Encode paramaters as Object to querystring
         * @param  {Object} params The parameters to encode
         * @return {String}        The URL encoded querystring
         */
        encodeParams(params) {
            return Object.keys(params).map(key => {
                return [key, params[key]].map(encodeURIComponent).join('=');
            }).join('&');
        }

        /**
         * Build a complete URL
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} params  Optionnal query strings parameters
         * @return {String}         The full URL
         */
        build(url, params) {
            if (!this.isAbsolute(url)) {
                url  = `${this.ROOT}/${url}`;
            }
            if (params) {
                const parts = [url, this.encodeParams(params)];
                url = url.indexOf('?') >= 0 ? parts.join('&') : parts.join('?');
            }
            return url;
        }

        /**
         * Default handler for JSON response
         * @param  {Response} response A response with JSON expected body.
         * @return {Promise}           A promise for data handling
         */
        jsonHandler(response) {
            // TODO: error handling
            return response.json();
        }

        /**
         * Perform a GET operation and process JSON
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} params  Optionnal query strings parameters
         * @param  {[type]} headers Optionnal HTTP headers
         * @return {Promise}        An instanciated fetch promise
         */
        get(url, params, headers) {
            return this.getRaw(url, params, headers).then(this.jsonHandler);
        }

        /**
         * Perform a GET operation
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} params  Optionnal query strings parameters
         * @param  {[type]} headers Optionnal HTTP headers
         * @return {Promise}        An instanciated fetch promise
         */
        getRaw(url, params, headers) {
            return fetch(this.build(url, params), {
                method: 'get',
                credentials: 'include',
                headers: Object.assign({}, DEFAULT_HEADERS, headers || {})
            });
        }

        /**
         * Perform a POST operation with a JSON payload
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} data    The body payload
         * @param  {[type]} headers Optionnal HTTP headers
         * @return {Promise}        An instanciated fetch promise
         */
        post(url, data, headers) {
            return fetch(this.build(url), {
                method: 'post',
                credentials: 'include',
                headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
                body: JSON.stringify(DATA)
            }).then(this.jsonHandler);
        }

        /**
         * Perform a POST upload operation (form/multipart)
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} data    The body payload
         * @param  {Object} headers Optionnal HTTP headers
         * @return {Promise}        An instanciated fetch promise
         */
        upload(url, data, headers) {
            const body = data;
            return fetch(this.build(url), {
                method: 'post',
                credentials: 'include',
                headers: Object.assign(
                    {'Content-Type': 'multipart/form-data'}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}
                ),
                body: body
            }).then(this.jsonHandler);
        }

        /**
         * Perform a PUT operation
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} data    The body payload
         * @param  {Object} headers Optionnal HTTP headers
         * @return {Promise}        An instanciated fetch promise
         */
        put(url, data, headers) {
            return fetch(this.build(url), {
                method: 'put',
                credentials: 'include',
                headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
                body: JSON.stringify(DATA)
            }).then(this.jsonHandler);
        }

        /**
         * Perform a DELETE operation
         * @param  {String} url     An absolute or API root relative URL
         * @param  {Object} headers Optionnal HTTP options
         * @return {Promise}        An instanciated fetch promise
         */
        delete(url, headers) {
            return fetch(this.build(url), {
                method: 'delete',
                credentials: 'include',
                headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
            }).then(this.jsonHandler);
        }
    }

    Vue.prototype.$api = Vue.api = new Api();
}
