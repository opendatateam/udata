import API from 'api';
import validator from 'models/validator';
import Vue from 'vue';
import {pubsub, PubSub} from 'pubsub';


function empty_schema() {
    return {properties: {}, required: []};
}

export class Model {

    constructor(options) {
        this.$options = options || {};
        this.$pubsub = new PubSub();
        this.empty();
    }

    /**
     * The class name
     * @return {[type]} [description]
     */
    get __class__() {
        return this.constructor.name
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
     * Call an API endpoint.
     * Callbacks are scoped to the model instance.
     *
     * @param  {String}   endpoint The API endpoint to call
     * @param  {Object}   data     The data object to submit
     * @param  {Function} callback The callback function to call on success.
     * @return {[type]}            [description]
     */
    $api(endpoint, data, callback) {
        var parts = endpoint.split('.'),
            namespace = parts[0],
            method = parts[1],
            operation = API[namespace][method];

        return operation(data, callback.bind(this));
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

    $on(name, hanler) {
        return this.$pubsub.subscribe(name, hanler);
    }

    $off(name, hanler) {
        return this.$pubsub.unsubscribe(name, hanler);
    }

    on_fetched(data) {
        for (let prop in data.obj) {
            let value = data.obj[prop];
            this._set(prop, value);
        }
        this.$emit('updated');
        this.loading = false;
    }

    validate() {
        return validator.validateMultiple(this, this.__schema__);
    }

    clear() {
        empty(this.$data, this.schema);
        return this;
    }
};


export class List extends Model {
    constructor(options) {
        super(options);
        this.items = [];
        this.query = this.$options.query || {};
        this.loading = false;
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

    by_id(id) {
        var filtered = this.items.filter(function(item) {
            return item.hasOwnProperty('id') && item.id === id;
        });
        return filtered.length === 1 ? filtered[0] : null;
    }

    clear() {
        this.items = [];
        this.$emit('updated');
        return this;
    }
};


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

        return op.parameters.filter(function(p) {
            return p.name == 'q';
        }).length > 0;
    }

    /**
     * Fetch page from server.
     * @param  {[type]} options [description]
     * @return {[type]}         [description]
     */
    fetch(options) {
        this.query = Object.assign(this.query, options || {});
        this.loading = true;
        this.$api(this.$options.ns + '.' + this.$options.fetch, this.query, this.on_fetched);
        return this;
    }

    next() {
        if (this.page && this.page < this.pages) {
            this.query.page = this.page + 1;
            this.fetch();
        }
    }

    previous() {
        if (this.page && this.page > 1) {
            this.query.page = this.page - 1;
            this.fetch();
        }
    }

    go_to_page(page) {
        this.fetch({page: page});
    }

    sort(field, reversed) {
        if (this.sorted !== field) {
            this.query.sort = '-' + field;
        } else {
            reversed = reversed || (this.sorted == field ? !this.reversed : false);
            this.query.sort = reversed ? '-' + field : field;
        }
        this.fetch({page: 1}); // Clear the pagination
    }

    search(query) {
        this.query.q = query;
        this.fetch({page: 1}); // Clear the pagination
    }
};


export class PageList extends List {

    constructor(options) {
        super(options);
        this.page = 1;
        this.page_size = 10;
        this.sorted = null;
        this.reversed = false;
        this.data = [];
    }

    /**
     * Total amount of pages
     * @return {int}
     */
    get pages() {
        return Math.ceil(this.items.length / this.page_size);
    }

    next() {
        if (this.page && this.page < this.pages) {
            this.page = this.page + 1;
        }
        this.data = this.build_page();
    }

    previous() {
        if (this.page && this.page > 1) {
            this.page = this.page - 1;
        }
        this.data = this.build_page();
    }

    go_to_page(page) {
        this.page = page;
        this.data = this.build_page();
    }

    sort(field, reversed) {
        this.sorted = field;
        this.reversed = reversed !== undefined ? reversed : !this.reversed;
        this.page = 1;
        this.data = this.build_page();
    }

    search(query) {
        console.log('search', query);
    }

    build_page() {
        return this.items
            .sort(function(a, b) {
                var valA = getattr(a, this.sorted),
                    valB = getattr(b, this.sorted);

                if (valA > valB) {
                    return this.reversed ? -1 : 1;
                } else if (valA < valB) {
                    return this.reversed ? 1 : -1;
                } else {
                    return 0;
                }
            }.bind(this))
            .slice(
                Math.max(this.page - 1, 0) * this.page_size,
                this.page * this.page_size
            );
    }
};
