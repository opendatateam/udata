'use strict';

import API from 'api';
import validator from 'models/validators';
import Vue from 'vue';

export default class Model {

    constructor(name options) {
        this.__name = name;
        this.__options = options || {};
        this.empty();
    }

    /**
     * The class name
     * @return {[type]} [description]
     */
    get __name__() {
        var constructor = this.constructor;
        while (constructor.name == 'VueComponent') {
            constructor = constructor.super;
        }
        return constructor.name
    }

    /**
     * Get the Swagger schema for a given Class.
     * @param  {Vue} cls A model Class with a declared name.
     * @return {Object} A JSON schema
     */
    get __schema__() {
        return API.definitions[this.__name__] || {};
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
     * Call an API endpoint.
     * Callbacks are scoped to the model instance.
     *
     * @param  {[type]}   endpoint [description]
     * @param  {[type]}   data     [description]
     * @param  {Function} callback [description]
     * @return {[type]}            [description]
     */
    $api(endpoint, data, callback) {
        var parts = endpoint.split('.');
            namespace = parts[0],
            method = parts[1];
            operation = API[namespace][method];

        return operation(data, callback.bind(this));
    }


    on_fetched(data) {
        var schema = this.schema,
            prop, value;

        for (prop in data.obj) {
            value = data.obj[prop];
            this.$set(prop, value)
        }
        // this.modelize(data.obj);
        // $.extend(true, this.$data, data.obj);
        this.$emit('updated', this);
        this.$dispatch(this.constructor.name.toLowerCase() + ':updated', this);
        this.loading = false;
    }

    validate() {
        return validator.validateMultiple(this.$data, this.schema);
    }

    clear() {
        empty(this.$data, this.schema);
        return this;
    }

    /**
     * Set values from a Raw object given the schema.
     * @param  {Object} raw    The raw object
     */
    modelize(raw) {
        var schema = this.schema,
            prop, value, def;

        for (prop in raw) {
            value = raw[prop];
            def = schema.properties[prop];
            // Nested object
            if (def.hasOwnProperty('$ref')) {
                var classname = def.$ref.replace('#/definitions/', '');

                    // Model =
                console.log('$ref', def.$ref);
                console.log(classname);
            }
            // Array of models
            else if (def.type == 'array' && def.items.hasOwnProperty('$ref')) {
                console.log('items.$ref', def.items.$ref);
                var classname = def.items.$ref.replace('#/definitions/', '');
                console.log(classname);
            }
            // Default: affectation is enough
            else {
                this.$set(prop, value);
            }
        }
    }

}
