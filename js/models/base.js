define(['api', 'models/validator', 'vue'], function(API, validator, Vue) {
    'use strict';

    /**
     * Fetch the class name for given Vue object instance
     * @param  {Object} cls a Vue instance
     * @return {string}     The class name, declared or inherited
     */
    function classname(cls) {
        var constructor = cls.constructor;
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
    function schema_for(cls) {
        return API.definitions[classname(cls)] || {};
    }

    /**
     * Empty or clear a data object based on a schema.
     * @param  {Object} obj    the object to empty.
     * @param  {Object} schema the schema to based empty values
     * @return {Object}        the updated data object
     */
    function empty(obj, schema) {
        for (var key in schema.properties) {
            if (schema.properties.hasOwnProperty(key)) {
                obj[key] = schema.required.indexOf(key) >= 0 ? null : undefined;
            }
        }
        return obj;
    }


    /**
     * A Swagger model base class
     */
    var Model = Vue.extend({
        /**
         * Declare bindable attributes from Swagger Specifications
         */
        data: function() {
            return empty({loading: false}, schema_for(this));
        },
        computed: {
            classname: function() {
                return classname(this);
            },
            schema: function() {
                return schema_for(this);
            }
        },
        methods: {
            on_fetched: function(data) {
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
            },
            validate: function() {
                return validator.validateMultiple(this.$data, this.schema);
            },
            clear: function() {
                empty(this.$data, this.schema);
                return this;
            },
            /**
             * Set values from a Raw object given the schema.
             * @param  {Object} raw    The raw object
             */
            modelize: function(raw) {
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
    });

    return Model;

});
