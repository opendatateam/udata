import config from 'config';
import CustomError from 'error';
import log from 'logger';


export class ApiError extends CustomError {
    constructor(response, data) {
        const message = data && data.hasOwnProperty('message')
            ? data.message
            : response.statusText || 'API Error';

        super(message);

        this.response = response;
        this.status = response.status;
        this.data = data;
    }
}


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


/**
 * Wrap fetch() calls with predefined API parameters
 */
export class Api {
    constructor(root) {
        // Compute the root once
        root = root || '';
        this.root = root.endsWith('/')
            ? root.substring(0, root.length - 1)
            : root;
        // Expose ApiError as Vue.api.Error
        this.Error = ApiError;
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
        return Object.keys(params).map(key =>
            [key, params[key]].map(encodeURIComponent).join('=')
        ).join('&');
    }

    /**
     * Build a complete URL
     * @param  {String} url     An absolute or API root relative URL
     * @param  {Object} params  Optional query strings parameters
     * @return {String}         The full URL
     */
    build(url, params) {
        if (!this.isAbsolute(url)) {
            url  = `${this.root}/${url}`;
        }
        if (params && Object.keys(params).length) {
            const parts = [url, this.encodeParams(params)];
            url = url.indexOf('?') >= 0 ? parts.join('&') : parts.join('?');
        }
        return url;
    }

    /**
     * Default handler for JSON response
     * Parse the response if OK otherwise throw it
     * (let the developper handle it in the catch() handler)
     * @param  {Response} response A response with JSON expected body.
     * @return {Promise}           A promise for data handling
     */
    onResponse(response) {
        if (response.ok) {
            return response.json();
        } else {
            return response.json()
                .catch(() => Promise.reject(new ApiError(response)))
                .then(json => Promise.reject(new ApiError(response, json)));
        }
    }


    /**
     * Generic error handler
     * @param  {[type]} error [description]
     * @return {[type]}       [description]
     */
    onError(error) {
        if (error instanceof Response) {
            error = new ApiError(response);
        }
        log.error('Unhandled API error:', error);
        return Promise.reject(error);
    }

    /**
     * Perform a GET operation
     * @param  {String} url     An absolute or API root relative URL
     * @param  {Object} params  Optional query strings parameters
     * @param  {[type]} headers Optional HTTP headers
     * @return {Promise}        An instanciated fetch promise
     */
    get(url, params, headers) {
        return fetch(this.build(url, params), {
                method: 'get',
                credentials: 'include',
                headers: Object.assign({}, DEFAULT_HEADERS, headers || {})
            })
            .catch(this.onError)
            .then(this.onResponse);
    }

    /**
     * Perform a POST operation with a JSON payload
     * @param  {String} url     An absolute or API root relative URL
     * @param  {Object} data    The body payload
     * @param  {[type]} headers Optional HTTP headers
     * @return {Promise}        An instanciated fetch promise
     */
    post(url, data, headers) {
        return fetch(this.build(url), {
            method: 'post',
            credentials: 'include',
            headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
            body: JSON.stringify(data)
        })
        .catch(this.onError)
        .then(this.onResponse);
    }

    /**
     * Perform a PUT operation
     * @param  {String} url     An absolute or API root relative URL
     * @param  {Object} data    The body payload
     * @param  {Object} headers Optional HTTP headers
     * @return {Promise}        An instanciated fetch promise
     */
    put(url, data, headers) {
        return fetch(this.build(url), {
            method: 'put',
            credentials: 'include',
            headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
            body: JSON.stringify(data)
        })
        .catch(this.onError)
        .then(this.onResponse);
    }

    /**
     * Perform a DELETE operation
     * @param  {String} url     An absolute or API root relative URL
     * @param  {Object} headers Optional HTTP options
     * @return {Promise}        An instanciated fetch promise
     */
    delete(url, headers) {
        return fetch(this.build(url), {
            method: 'delete',
            credentials: 'include',
            headers: Object.assign({}, DEFAULT_HEADERS, WRITE_HEADERS, headers || {}),
        })
        .catch(this.onError)
        .then(this.onResponse);
    }
}


export function install(Vue) {
    // Tha wrapper is accessible on Vue.api or this.$api on instances
    Vue.prototype.$api = Vue.api = new Api(config.api_root);
}
