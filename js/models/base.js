import API from 'api';
import validator from 'models/validator';
import {pubsub, PubSub} from 'pubsub';
import Sifter from 'sifter';
import Vue from 'vue';

import mask from './mask';

export const DEFAULT_PAGE_SIZE = 10;

/**
 * This request interceptor add the missing jQuery.ajax contentType parameters
 * when required (ie. when swagger has set the proper Content-Type header)
 */
const requestInterceptor = {
    apply(obj) {
        if (obj.headers['Content-Type']) {
            obj.contentType = obj.headers['Content-Type'];
        }
        return obj;
    }
}

/**
 * Common class behaviors.
 *
 * Provide:
 *     - PubSub
 *     - Scoped API access
 *     - Vue.js compatible setter
 */
export class Base {
    constructor(options) {
        this.$pubsub = new PubSub();
        this.$options = options || {};
        if (this.$options.loading !== undefined) {
            this.loading = Boolean(this.$options.loading);
        } else {
            this.loading = this.$options.data === undefined;
        }
    }

    /**
     * The class name
     * @return {[type]} [description]
     */
    get __class__() {
        return this.constructor.name;
    }

    /**
     * Property setter which handle vue.js $set method if object is binded.
     * @param {String} name  The name of the object property to set.
     * @param {Object} value The property value to set.
     */
    _set(name, value) {
        if (this.hasOwnProperty('__ob__')) {
            Vue.set(this, name, value);
            // this.$set(name, value);
        } else {
            this[name] = value;
        }
    }

    /**
     * Emit an event on this model instance
     * @param  {String} name    The event unique name
     * @param  {Array}  args    A variable number of parameters
     */
    $emit(name, ...args) {
        const prefix = this.__class__.toLowerCase();
        const topic = prefix + ':' + name;
        pubsub.publish(topic, this, ...args);
        this.$pubsub.publish(name, this, ...args);
    }

    /**
     * Register a listener on an event.
     * @param  {String}   name   The event name to subscribe
     * @param  {Function} handler The callback to register
     * @return {Object}   An object with a single method remove
     *                       allowing to unregister the callback
     */
    $on(name, handler) {
        return this.$pubsub.subscribe(name, handler);
    }

    /**
     * Unregister a listener on an event.
     * @param  {String}   name   The event name to subscribe
     * @param  {Function} handler The callback to register
     */
    $off(name, handler) {
        return this.$pubsub.unsubscribe(name, handler);
    }

    /**
     * Register once a listener on an event.
     * @param  {String}   name   The event name to subscribe
     * @param  {Function} handler The callback to register
     */
    $once(name, handler) {
        return this.$pubsub.once(name, handler);
    }

    /**
     * Call an API endpoint.
     * Callbacks are scoped to the model instance.
     *
     * @param  {String}   endpoint The API endpoint to call
     * @param  {Object}   data     The data object to submit
     * @param  {Function} on_success The callback function to call on success.
     * @param  {Function} on_error The callback function to call on error.
     */
    $api(endpoint, data, on_success, on_error = () => {}) {
        API.onReady(() => {
            const [namespace, method] = endpoint.split('.');
            const operation = API[namespace][method];
            const opts = {requestInterceptor};

            if (this.$options.mask && !('X-Fields' in data)) {
                data['X-Fields'] = mask(this.$options.mask);
            }

            operation(data, opts, on_success.bind(this), on_error.bind(this));
        });
    }
}

/**
 * A base class for schema based models.
 */
export class Model extends Base {
    constructor(options) {
        super(options);
        API.onReady(this.empty.bind(this));
        if (this.$options.data) {
            Object.assign(this, this.$options.data);
        }
    }

    /**
     * Get the JSON schema for a given Class from Swagger definitions.
     * @param  {Vue} cls A model Class with a declared name.
     * @return {Object} A JSON schema
     */
    get __schema__() {
        return API.definitions[this.__class__] || {};
    }

    /**
     * Empty or clear a data object based on a schema.
     * @return {Object}     The instance
     */
    empty() {
        const schema = this.__schema__;
        for (const key in schema.properties) {
            if (schema.properties.hasOwnProperty(key)) {
                if (schema.properties[key].type === 'array') {
                    this._set(key, []);
                } else if (schema.required.indexOf(key) >= 0) {
                    this._set(key, null);
                } else {
                    this._set(key, undefined);
                }
            }
        }
        return this;
    }

    on_fetched(data) {
        for (const prop in data.obj) {
            if (data.obj.hasOwnProperty(prop)) {
                this._set(prop, data.obj[prop]);
            }
        }
        this.$emit('updated');
        this.loading = false;
    }

    /**
     * Perform a model validation given its schema
     * @return {Object} A TV4 validation descriptor.
     */
    validate() {
        return validator.validateMultiple(this, this.__schema__);
    }

    /**
     * Empty the model
     * @return {Object} Return itself allowing to chain methods.
     */
    clear() {
        this.empty();
        return this;
    }
}


/**
 * A base class for unpaginated list
 */
export class List extends Base {
    constructor(options) {
        super(options);

        this.items = this.$options.data || [];
        this.query = this.$options.query || {};
        this.model = this.$options.model;

        this.sorted = null;
        this.reversed = false;
        this.filtered_data = [];
        this._search = '';
        this.populate();
    }

    get has_search() {
        return this.$options.search !== undefined;
    }

    get has_data() {
        return this.items.length > 0;
    }

    get data() {
        return this.filtered_data;
    }

    set data(value) {
        this._set('filtered_data', value);
    }

    /**
     * Populate the data view (filtered and sorted)
     */
    populate() {
        const options = {nesting: true};
        const sifter = new Sifter(this.items);

        if (this.$options.search) {
            options.fields = Array.isArray(this.$options.search) ? this.$options.search : [this.$options.search];
        } else {
            options.fields = [];
        }

        if (this.sorted) {
            options.sort = [{
                field: this.sorted,
                direction: this.reversed ? 'desc' : 'asc'
            }];
        }

        this.data = sifter.search(this._search, options).items.map((result) => {
            return this.items[result.id];
        });
    }

    /**
     * Fetch an unpaginated list.
     * @param  {[type]} options [description]
     * @return {[type]}         [description]
     */
    fetch(options) {
        options = Object.assign(this.query, options);
        this.loading = true;
        this.$api(this.$options.ns + '.' + this.$options.fetch, options, this.on_fetched);
        return this;
    }

    on_fetched(data) {
        this.items = this.model ? data.obj.map(o => new this.model({data: o})) : data.obj;
        this.populate();
        this.$emit('updated');
        this.loading = false;
    }

    /**
     * Get an item given its ID
     */
    by_id(id) {
        const filtered = this.items.filter((item) => {
            return item.hasOwnProperty('id') && item.id === id;
        });
        return filtered.length === 1 ? filtered[0] : null;
    }

    /**
     * Empty the list
     * @return {Object} Return itself allowing to chain methods.
     */
    clear() {
        this.items = [];
        this.populate();
        this.$emit('updated');
        return this;
    }


    /**
     * Perform a client-side sort
     * @param {String} field The object attribute to sort on.
     * @param {Boolean} reversed If true, sort is descending.
     * @return {Object} Return itself allowing to chain methods.
     */
    sort(field, reversed) {
        this.sorted = field;
        this.reversed = reversed !== undefined ? reversed : !this.reversed;
        this.page = 1;
        this.populate();
        return this;
    }

    /**
     * Perform a client-side search
     * @param  {String} query The query string to perform the search on.
     * @return {Object} Return itself allowing to chain methods.
     */
    search(query) {
        this._search = query;
        this.sorted = null;
        this.populate();
        return this;
    }
}

/**
 * A base class for server-side paginated list.
 */
export class ModelPage extends Model {
    constructor(options) {
        super(options);
        this.query = this.$options.query || {};
        this.cumulative = this.$options.cumulative || false;
        if (this.$options.mask) {
            this.query['X-Fields'] =  `data{${mask(this.$options.mask)}},*`;
        }
        this.loading = true;
        this.serverside = true;
        this._data = [];
    }

    /**
     * Total amount of pages
     * @return {int}
     */
    get pages() {
        return Math.ceil(this.total / this.page_size);
    }

    /**
     * Field name used for sorting
     * @return {string}
     */
    get sorted() {
        if (!this.query.sort) {
            return;
        }
        return this.query.sort[0] === '-'
            ? this.query.sort.substring(1, this.query.sort.length)
            : this.query.sort;
    }

    /**
     * Wether the sort is reversed (descending) or not (ascending)
     * @return {boolean}
     */
    get reversed() {
        if (!this.query.sort) {
            return;
        }
        return this.query.sort[0] === '-';
    }

    get has_search() {
        const op = API[this.$options.ns].operations[this.$options.fetch];

        return op.parameters.filter((p) => {
            return p.name === 'q';
        }).length > 0;
    }

    get has_data() {
        return this.data && this.data.length;
    }

    /**
     * Fetch page from server.
     * @param  {Object} options An optional query object
     * @return {Object} Return itself allowing to chain methods.
     */
    fetch(options) {
        this.query = Object.assign(this.query, options || {});
        this.loading = true;
        this.$api(this.$options.ns + '.' + this.$options.fetch, this.query, this.on_fetched);
        return this;
    }

    on_fetched(data) {
        if (this.cumulative && this._data.length) {
            data.obj.data = this._data.concat(data.obj.data);
        }
        super.on_fetched(data);
        this._data = data.obj.data;
        this.$emit('updated');
    }

    /**
     * Fetch the next page.
     * @param {Object} options An optional query object for fetch.
     * @return {Object} Return itself allowing to chain methods.
     */
    nextPage(options) {
        if (this.page && this.page < this.pages) {
            this.query.page = this.page + 1;
            this.fetch(options);
        }
        return this;
    }

    /**
     * Fetch the previous page.
     * @return {Object} Return itself allowing to chain methods.
     */
    previousPage() {
        if (this.page && this.page > 1) {
            this.query.page = this.page - 1;
            this.fetch();
        }
        return this;
    }

    /**
     * Fetch a page given its index.
     * @param {Number} page The page index to fetch.
     * @return {Object} Return itself allowing to chain methods.
     */
    go_to_page(page) {
        this.fetch({page: page});
        return this;
    }

    /**
     * Perform a server-side sort
     * @param {String} field The object attribute to sort on.
     * @param {Boolean} reversed If true, sort is descending.
     * @return {Object} Return itself allowing to chain methods.
     */
    sort(field, reversed) {
        if (this.sorted !== field) {
            this.query.sort = '-' + field;
        } else {
            reversed = reversed || (this.sorted === field ? !this.reversed : false);
            this.query.sort = reversed ? '-' + field : field;
        }
        this.fetch({page: 1}); // Clear the pagination
        return this;
    }

    /**
     * Perform a server-side search
     * @param  {String} query The query string to perform the search on.
     * @return {Object} Return itself allowing to chain methods.
     */
    search(query) {
        this.query.q = query;
        this.query.sort = undefined;
        this.fetch({page: 1}); // Clear the pagination
        return this;
    }
}

/**
 * A client-side pager wrapper for list.
 */
export class PageList extends List {
    constructor(options) {
        super(options);
        this.page = 1;
        this.page_size = this.$options.page_size || DEFAULT_PAGE_SIZE;
    }

    get data() {
        return super.data.slice(
            Math.max(this.page - 1, 0) * this.page_size,
            this.page * this.page_size
        );
    }

    set data(value) {
        this._set('filtered_data', value);
    }

    /**
     * Total amount of pages
     * @return {int}
     */
    get pages() {
        return Math.ceil(this.filtered_data.length / this.page_size);
    }

    /**
     * Display the next page.
     * @return {Object} Return itself allowing to chain methods.
     */
    nextPage() {
        if (this.page && this.page < this.pages) {
            this.go_to_page(this.page + 1);
        }
        return this;
    }

    /**
     * Display the previous page.
     * @return {Object} Return itself allowing to chain methods.
     */
    previousPage() {
        if (this.page && this.page > 1) {
            this.go_to_page(this.page - 1);
        }
        return this;
    }

    /**
     * Display a page given its index.
     * @param {Number} page The page index to fetch.
     * @return {Object} Return itself allowing to chain methods.
     */
    go_to_page(page) {
        this.page = page;
        this.populate();
        return this;
    }

    /**
     * Useful to clear the paging after server-based filtering.
     */
    on_fetched(data) {
        super.on_fetched(data);
        this.page = 1;  // Clear the paging
    }
}
