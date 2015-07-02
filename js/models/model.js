'use strict';

import API from 'api';
import validator from 'models/validator';
import Vue from 'vue';
import {pubsub, PubSub} from 'pubsub';


function empty_schema() {
    return {properties: {}, required: []};
}

export default class Model {

    constructor(options) {
        this._options = options || {};
        this._pubsub = new PubSub();
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
        this._pubsub.publish(name, this, args)
    }

    $on(name, hanler) {
        return this._pubsub.subscribe(name, hanler);
    }

    $off(name, hanler) {
        return this._pubsub.unsubscribe(name, hanler);
    }

    on_fetched(data) {
        console.log('on fetched', data);
        // var schema = this.schema;

        for (let prop in data.obj) {
            let value = data.obj[prop];
            this._set(prop, value);
        }
        console.log('validate', this.validate());
        // this.modelize(data.obj);
        // $.extend(true, this.$data, data.obj);
        this.$emit('updated');
        this.loading = false;
        console.log(this);
    }

    validate() {
        return validator.validateMultiple(this, this.__schema__);
    }

    clear() {
        empty(this.$data, this.schema);
        return this;
    }

    // /**
    //  * Set values from a Raw object given the schema.
    //  * @param  {Object} raw    The raw object
    //  */
    // modelize(raw) {
    //     var schema = this.schema,
    //         prop, value, def;

    //     for (prop in raw) {
    //         value = raw[prop];
    //         def = schema.properties[prop];
    //         // Nested object
    //         if (def.hasOwnProperty('$ref')) {
    //             var classname = def.$ref.replace('#/definitions/', '');

    //                 // Model =
    //             console.log('$ref', def.$ref);
    //             console.log(classname);
    //         }
    //         // Array of models
    //         else if (def.type == 'array' && def.items.hasOwnProperty('$ref')) {
    //             console.log('items.$ref', def.items.$ref);
    //             var classname = def.items.$ref.replace('#/definitions/', '');
    //             console.log(classname);
    //         }
    //         // Default: affectation is enough
    //         else {
    //             this.$set(prop, value);
    //         }
    //     }
    // }

}
