/**
 * Cache based on Web Storage (session or local)
 */

function now() {
    return new Date().getTime();
}

/**
 * A WebStorage shim.
 *
 * To use as fallback when WebStorage is not available
 * or when access to webstorage is not allowed.
 *
 * This storage has poor performance and won't survive page change or reload.
 */
export class ShimStorage {
    constructor() {
        this.store = {};
    }

    get length() {
        return Object.keys(this.store).length;
    }

    key(idx) {
        return Object.keys(this.storage)[idx] || null;
    }

    getItem(key) {
        return this.store[key] || null;
    }

    setItem(key, value) {
        this.store[key] = value;
    }

    removeItem(key) {
        delete this.store[key];
    }

    clear() {
        this.store = {};
    }
}

/**
 * A WebStorage based cache with optional TTL (expressed in seconds).
 */
export class Cache {
    /**
     * Constructor
     * @param  {String} namespace The namespace key meant to isolate keys
     * @param  {int} ttl                An optional default TTL
     */
    constructor(namespace, ttl) {
        this.namespace = namespace;
        this.ttl = ttl;
        this.prefix = `__${this.namespace}__`;
        this.rekey = new RegExp(`^${this.prefix}`);
        try {
            this.storage = sessionStorage;
            // Force error if sessions storage is simply not defined
            if (!this.storage) throw Error('Session storage is missing');
        } catch(e) {
            // Session storage access is not allowed (browser privacy settings)
            // A warning is issued in the console
            const msg = `Access to sessionStorage is not possible.\
            "${namespace}" cache performances will be degraded`;
            console.warn(msg);  // eslint-disable-line no-console
            this.storage = new ShimStorage();
        }
    }

    /**
     * Build the namespace key
     * @param  {String} key The public raw key to be namespaced
     * @return {String}     The namespaced key
     */
    _key(key) {
        return this.prefix + key;
    }

    /**
     * Prefix the namespace ttl key
     * @param  {String} key The public raw key to be namespaced
     * @return {String}     The namespace ttl key
     */
    _ttl(key) {
        return `${this.prefix}__ttl__${key}`;
    }

    /**
     * List all cache keys in the storage
     * @return {Array} All existing cache keys
     */
    get keys() {
        return [...Array(this.storage.length).keys()]
            .map(idx => this.storage.key(idx))
            .filter(key => this.rekey.test(key))
            .map(key => key.replace(this.rekey, ''));
    }

    /**
     * Get value from its key
     * @param  {String} key The cache key
     * @return {Object}     The value if exists, undefined otherwise
     */
    get(key) {
        if (this.isExpired(key)) {
            this.remove(key);
        }

        const value = this.storage.getItem(this._key(key));
        if (value) return JSON.parse(value);
    }

    /**
     * Insert or update a cached value
     * @param {String} key   The cache key
     * @param {Object} value The value to cache
     * @param {int} ttl   an optional TTL (override the default TTL)
     * @return {Object} The cache instance (allow chaining)
     */
    set(key, value, ttl) {
        if (Number.isInteger(ttl) || Number.isInteger(this.ttl)) {
            ttl = Number.isInteger(ttl) ? ttl : this.ttl;
            this.storage.setItem(this._ttl(key), now() + ttl);
        } else {
           this.storage.removeItem(this._ttl(key));
        }

        this.storage.setItem(this._key(key), JSON.stringify(value));
        return this;
    }

    /**
     * Remove a value from the cache given its key
     * @param {String} key   The cache key
     * @return {Object} The cache instance (allow chaining)
     */
    remove(key) {
        this.storage.removeItem(this._ttl(key));
        this.storage.removeItem(this._key(key));
        return this;
    }

    /**
     * Empty the cache (remove all keys)
     * @return {Object} The cache instance (allow chaining)
     */
    clear() {
        this.keys.forEach(key => this.remove(key));
        return this;
    }

    /**
     * Check if a cached value is expired
     * @param {String} key   The cache key
     * @return {Boolean}     true if the cached value expired
     */
    isExpired(key) {
        const ttl = JSON.parse(this.storage.getItem(this._ttl(key)));
        return Number.isInteger(ttl) && now() > ttl;
    }
}


export const cache = new Cache('udata');

export default cache;
