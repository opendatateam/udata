define(['api', 'vue', 'jquery'], function(API, Vue, $) {
    'use strict';

    var ModelList = Vue.extend({
        /**
         * Declare bindable attribute from Swagger Specifications
         */
        data: function() {
            return {
                items: [],
                query: {},
                loading: false
            };
        },
        methods: {
            /**
             * Fetch a paginated list.
             * @param  {[type]} options [description]
             * @return {[type]}         [description]
             */
            fetch: function(options) {
                options = $.extend(this.query, this.$options.query, options);
                this.loading = true;
                API[this.$options.ns][this.$options.fetch](options, this.on_fetched.bind(this));
                return this;
            },
            on_fetched: function(data) {
                while (this.items.length > 0) {
                    this.items.pop();
                }
                for (var i=0; i < data.obj.length; i++) {
                    this.items.push(data.obj[i]);
                }
                this.$emit('updated', this);
                this.loading = false;
            },
            by_id: function(id) {
                var filtered = this.items.filter(function(item) {
                    return item.hasOwnProperty('id') && item.id === id;
                });
                return filtered.length === 1 ? filtered[0] : null;
            }
        }
    });

    return ModelList;

});
