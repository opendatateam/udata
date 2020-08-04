/**
 * A Basic OEmbed loader for udata cards.
 *
 * This is only required in case standard OEmbed is not available
 * or udata is not whitelisted on a given platform.
 *
 * Instead of simply putting URL, this script requires to `div`
 * with `data-udata-*` attributes:
 *
 * Ex:
 *      <div data-udata-dataset="slug-or-id"></div>
 *      <div data-udata-reuse="slug-or-id"></div>
 *      <div data-udata-organization="slug-or-id"></div>
 */
import 'whatwg-fetch';
import '../less/oembed.less';

/**
 * Extract the base URL from the URL of the current script
 */
function getBaseUrl() {
    const script =  document.currentScript || document.querySelector('script[src$="oembed.js"]');
    const parser = document.createElement('a');
    parser.href = script.dataset.udata || script.src;
    return `${parser.protocol}//${parser.host}`;
}

// Base udata instance URL
const BASE_URL = getBaseUrl();
// OEmbed endpoint URL
const OEMBED_URL = `${BASE_URL}/api/1/oembed`;
// Loads cards in the same language than the current site
const LANG = document.documentElement.lang;
// Supported attributes
const ATTRS = ['dataset', 'reuse'];


/**
 * `fetch` doesn't provide an error handling based on status code.
 */
function checkStatus(response) {
    if (response.status >= 200 && response.status < 300) {
        return response;
    } else {
        const error = new Error(response.statusText);
        error.response = response;
        throw error;
    }
}

/**
 * Return a promisified JSON response from an API URL
 * if status code is correct.
 */
function fetchOEmbed(url) {
    return fetch(`${OEMBED_URL}?url=${encodeURIComponent(url)}`)
        .then(checkStatus)
        .then(response => response.json());
}

/**
 * Transform a string to title case
 */
function toTitle(txt) {
    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
}

(function() {
    // Load cards for supported attributes
    ATTRS.forEach(function(attr) {
        [].forEach.call(document.querySelectorAll(`[data-udata-${attr}]`), function(div) {
            div.innerHTML = '<span class="fa fa-spin fa-spinner"></span>';
            const id = div.dataset[`udata${toTitle(attr)}`];
            fetchOEmbed(`${BASE_URL}/${LANG}/${attr}s/${id}/`)
                .then(oembed => {
                    div.innerHTML = oembed.html;
                });
        });
    });
})();
