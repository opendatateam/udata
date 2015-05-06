define(['api', 'models/base', 'jquery'], function(API, Model, $) {
    'use strict';

    var ModelPage = Model.extend({
        name: 'ModelPage',
        data: function() {
            return {
                query: {},
                loading: true,
                serverside: true
            };
        },
        computed: {
            /**
             * Total amount of pages
             * @return {int}
             */
            pages: function() {
                return Math.ceil(this.total / this.page_size);
            },
            /**
             * Field name used for sorting
             * @return {string}
             */
            sorted: function() {
                if (!this.query.sort) {
                    return;
                }
                return this.query.sort[0] == '-'
                    ? this.query.sort.substring(1, this.query.sort.length)
                    : this.query.sort;
            },
            /**
             * Wether the sort is reversed (descending) or not (ascending)
             * @return {boolean}
             */
            reversed: function() {
                if (!this.query.sort) {
                    return;
                }
                return this.query.sort[0] == '-';
            },
            has_search: function() {
                var op = API[this.$options.ns].operations[this.$options.fetch];

                return op.parameters.filter(function(p) {
                    return p.name == 'q';
                }).length > 0;
            }
        },
        methods: {
            /**
             * Fetch page from server.
             * @param  {[type]} options [description]
             * @return {[type]}         [description]
             */
            fetch: function(options) {
                this.query = $.extend({}, this.$options.query, this.query, options || {});
                this.loading = true;
                API[this.$options.ns][this.$options.fetch](this.query, this.on_fetched.bind(this));
                return this;
            },
            next: function() {
                if (this.page && this.page < this.pages) {
                    this.query.page = this.page + 1;
                    this.fetch();
                }
            },
            previous: function() {
                if (this.page && this.page > 1) {
                    this.query.page = this.page - 1;
                    this.fetch();
                }
            },
            go_to_page: function(page) {
                this.fetch({page: 1});
            },
            sort: function(field, reversed) {
                if (this.sorted !== field) {
                    this.query.sort = '-' + field;
                } else {
                    reversed = reversed || (this.sorted == field ? !this.reversed : false);
                    this.query.sort = reversed ? '-' + field : field;
                }
                this.fetch({page: 1}); // Clear the pagination
            },
            search: function(query) {
                this.query.q = query;
                this.fetch({page: 1}); // Clear the pagination
            }
        }
    });

    return ModelPage;
});
