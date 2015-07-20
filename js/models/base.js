import API from 'api';
import validator from 'models/validator';
import {pubsub, PubSub} from 'pubsub';



/**
 * An empty JSON schema factory
 * @return {Object} An empty JSON schema
 */
function empty_schema() {
    return {properties: {}, required: []};
}

/**
 * A property getter resolving dot-notation
 * @param  {Object} obj  The root object to fetch property on
 * @param  {String} name The optionnaly dotted property name to fetch
 * @return {Object}      The resolved property value
 */
function getattr(obj, name) {
    if (!obj || !name) return;
    var names = name.split(".");
    while(names.length && (obj = obj[names.shift()]));
    return obj;
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
    constructor() {
        this.$pubsub = new PubSub();
    }

    /**
     * The class name
     * @return {[type]} [description]
     */
    get __class__() {
        return this.constructor.name
    }

    /**
     * Property setter which handle vue.js $set method if object is binded.
     * @param {String} name  The name of the object proprty to set.
     * @param {Object} value The property value to set.
     */
    _set(name, value) {
        if (this.hasOwnProperty('$set')) {
            this.$set(name, value);
        } else {
            this[name] = value;
        }
    }

    /**
     * Emit an event on this model instance
     * @param  {String} name    The event unique name
     * @param  {Object} options An optionnal options object
     */
    $emit(name, ...args) {
        var prefix = this.__class__.toLowerCase(),
            topic = prefix + ':' + name;
        pubsub.publish(topic, this, ...args);
        this.$pubsub.publish(name, this, args)
    }

    /**
     * Register a listener on an event.
     * @param  {String}   name   The event name to subscribe
     * @param  {Function} hanler The callback to register
     * @return {Object}   An object with a single method remove
     *                       allowing to unregister the callback
     */
    $on(name, hanler) {
        return this.$pubsub.subscribe(name, hanler);
    }

    /**
     * Unregister a listener on an event.
     * @param  {String}   name   The event name to subscribe
     * @param  {Function} hanler The callback to register
     */
    $off(name, hanler) {
        return this.$pubsub.unsubscribe(name, hanler);
    }

    /**
     * Call an API endpoint.
     * Callbacks are scoped to the model instance.
     *
     * @param  {String}   endpoint The API endpoint to call
     * @param  {Object}   data     The data object to submit
     * @param  {Function} callback The callback function to call on success.
     */
    $api(endpoint, data, callback) {
        var parts = endpoint.split('.'),
            namespace = parts[0],
            method = parts[1],
            operation = API[namespace][method];

        return operation(data, callback.bind(this));
    }
};

/**
 * A base class for schema based models.
 */
export class Model extends Base {
    constructor(options) {
        super();
        this.$options = options || {};
        this.empty();
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
     * @param  {Object} obj    the object to empty.
     * @param  {Object} schema the schema to based empty values
     * @return {Object}        the updated data object
     */
    empty() {
        var schema = this.__schema__
        for (var key in schema.properties) {
            if (schema.properties.hasOwnProperty(key)) {
                this[key] = schema.required.indexOf(key) >= 0 ? null : undefined;
            }
        }
        return this;
    }

    on_fetched(data) {
        for (let prop in data.obj) {
            let value = data.obj[prop];
            this._set(prop, value);
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
};


/**
 * A base class for unpaginated list
 */
export class List extends Base {
    constructor(options) {
        super();
        this.$options = options || {};

        this.items = [];
        this.query = this.$options.query || {};
        this.loading = false;
    }

    get data() {
        return this.items;
    }

    /**
     * The class name
     * @return {[type]} [description]
     */
    get __class__() {
        return this.constructor.name
    }

    /**
     * Fetch a paginated list.
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
        while (this.items.length > 0) {
            this.items.pop();
        }
        for (var i=0; i < data.obj.length; i++) {
            this.items.push(data.obj[i]);
        }
        this.$emit('updated', this);
        this.loading = false;
    }

    /**
     * Get an item given its ID
     */
    by_id(id) {
        var filtered = this.items.filter((item) => {
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
        this.$emit('updated');
        return this;
    }
};

/**
 * A base class for server-side paginted list.
 */
export class ModelPage extends Model {
    constructor(options) {
        super(options);
        this.query = this.$options.query || {};
        this.loading = true;
        this.serverside = true;
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
        return this.query.sort[0] == '-'
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
        return this.query.sort[0] == '-';
    }

    get has_search() {
        var op = API[this.$options.ns].operations[this.$options.fetch];

        return op.parameters.filter((p) => {
            return p.name == 'q';
        }).length > 0;
    }

    /**
     * Fetch page from server.
     * @param  {Object} options An optionnal query object
     * @return {Object} Return itself allowing to chain methods.
     */
    fetch(options) {
        this.query = Object.assign(this.query, options || {});
        this.loading = true;
        this.$api(this.$options.ns + '.' + this.$options.fetch, this.query, this.on_fetched);
        return this;
    }

    /**
     * Fetch the next page.
     * @return {Object} Return itself allowing to chain methods.
     */
    nextPage() {
        if (this.page && this.page < this.pages) {
            this.query.page = this.page + 1;
            this.fetch();
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
            reversed = reversed || (this.sorted == field ? !this.reversed : false);
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
        this.fetch({page: 1}); // Clear the pagination
        return this;
    }
};

/**
 * A client-side pager wrapper for list.
 */
export class PageList extends List {
    constructor(options) {
        super(options);
        this.page = 1;
        this.page_size = 10;
        this.sorted = null;
        this.reversed = false;
        this.pager = [];

        this.$on('updated', () => {
            this.data = this.build_page();
        });
    }

    /**
     * Total amount of pages
     * @return {int}
     */
    get pages() {
        return Math.ceil(this.items.length / this.page_size);
    }

    get data() {
        return this.pager;
    }

    set data(value) {
        this._set('pager', value);
    }

    /**
     * Display the next page.
     * @return {Object} Return itself allowing to chain methods.
     */
    nextPage() {
        if (this.page && this.page < this.pages) {
            this.page = this.page + 1;
        }
        this.data = this.build_page();
        return this;
    }

    /**
     * Display the previous page.
     * @return {Object} Return itself allowing to chain methods.
     */
    previousPage() {
        if (this.page && this.page > 1) {
            this.page = this.page - 1;
        }
        this.data = this.build_page();
        return this;
    }

    /**
     * Display a page given its index.
     * @param {Number} page The page index to fetch.
     * @return {Object} Return itself allowing to chain methods.
     */
    go_to_page(page) {
        this.page = page;
        this.data = this.build_page();
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
        this.data = this.build_page();
        return this;
    }

    /**
     * Perform a client-side search
     * @param  {String} query The query string to perform the search on.
     * @return {Object} Return itself allowing to chain methods.
     */
    search(query) {
        console.log('search', query);
        return this;
    }

    build_page() {
        return this.items
            .sort((a, b) => {
                var valA = getattr(a, this.sorted),
                    valB = getattr(b, this.sorted);

                if (valA > valB) {
                    return this.reversed ? -1 : 1;
                } else if (valA < valB) {
                    return this.reversed ? 1 : -1;
                } else {
                    return 0;
                }
            })
            .slice(
                Math.max(this.page - 1, 0) * this.page_size,
                this.page * this.page_size
            );
    }
};
