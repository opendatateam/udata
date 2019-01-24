/**
 * Check if an object is a function
 */
export function isFunction(obj) {
    return obj && Object.prototype.toString.call(obj) === '[object Function]';
}

/**
 * Check if an object is an Object
 */
export function isObject(obj) {
    return obj === Object(obj);
}

/**
 * Check if an object is a String
 */
export function isString(obj) {
    return typeof obj === 'string' || obj instanceof String;
}

/**
 * A property getter resolving dot-notation
 * @param  {Object} obj  The root object to fetch property on
 * @param  {String} name The optionnaly dotted property name to fetch
 * @return {Object}      The resolved property value
 */
export function getattr(obj, name) {
    if (!obj || !name) return;
    const names = name.split('.');
    while(names.length && (obj = obj[names.shift()]));
    return obj;
}

/**
 * A property setter resolving dot-notation
 * @param  {Object} obj   The root object to set property on
 * @param  {String} name  The optionnaly dotted property name to set
 * @param  {Object} value The value to set
 */
export function setattr(obj, name, value) {
    if (!obj || !name) return;
    const names = name.split('.');
    while (names.length && (name = names.shift()) && names.length) {
        if (!obj.hasOwnProperty(name)) obj[name] = {};
        obj = obj[name];
    }
    obj[name] = value;
}

/**
 * Parse a query string into an object
 * @param  {String} qs  A querystring, with or without the leading '?'
 * @return {Object}     The parsed query string
 */
export function parseQS(qs) {
    const result = {};
    if (!qs || qs === '?') return result;
    if (qs.startsWith('?')) qs = qs.substr(1);
    qs.split('&').forEach(function(part) {
        const [key, value] = part.split('=');
        result[decodeURIComponent(key)] = decodeURIComponent(value.replace(/\+/g, '%20'));
    });
    return result;
}

/**
 * Escape special characters from a string for usage in a regex
 * @param  {String} str An unscaped string
 * @return {String}     The regex escaped string
 */
export function escapeRegex(str) {
    return str.replace(/[|\\{}()[\]^$+*?.]/g, '\\$&');
}

/**
 * Find the component containning a given element (if any)
 *
 * @param {VueComponent} $root The root component to search into
 * @param {Element} el The DOM element to match
 */
export function findComponent($root, el) {
    if ($root.$el === el) return $root;
    if (!$root.$el.contains(el)) return;  // Don't loop if not necessary

    let $match = $root;
    $root.$children.find($child => {
        $match = findComponent($child, el);
        return $match;
    });
    return $match;
}


export default {
    isFunction,
    isObject,
    isString,
    getattr,
    setattr,
    parseQS,
    escapeRegex,
    findComponent,
};
