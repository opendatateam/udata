define(['api', 'models/base_list', 'jquery'], function(API, List, $) {
    'use strict';

    function getattr(obj, name) {
        if (!obj || !name) return;
        var names = name.split(".");
        while(names.length && (obj = obj[names.shift()]));
        return obj;
    }

    var PageList = List.extend({
        /**
         * Declare bindable attribute from Swagger Specifications
         */
        data: function() {
            return {
                page: 1,
                page_size: 10,
                sorted: null,
                reversed: false,
                data: []
            };
        },
        computed: {
            /**
             * Total amount of pages
             * @return {int}
             */
            pages: function() {
                return Math.ceil(this.items.length / this.page_size);
            },
            // data: function() {
            //     return this.items
            //         .sort(function(a, b) {
            //             var valA = getattr(a, this.sorted),
            //                 valB = getattr(b, this.sorted);

            //             if (valA > valB) {
            //                 return this.reversed ? -1 : 1;
            //             } else if (valA < valB) {
            //                 return this.reversed ? 1 : -1;
            //             } else {
            //                 return 0;
            //             }
            //         }.bind(this))
            //         .slice(
            //             Math.max(this.page - 1, 0) * this.page_size,
            //             this.page * this.page_size
            //         );
            // }
        },
        methods: {
            next: function() {
                if (this.page && this.page < this.pages) {
                    this.page = this.page + 1;
                }
            },
            previous: function() {
                if (this.page && this.page > 1) {
                    this.page = this.page - 1;
                }
            },
            go_to_page: function(page) {
                this.page = page;
            },
            sort: function(field, reversed) {
                this.sorted = field;
                this.reversed = reversed !== undefined ? reversed : !this.reversed;
                this.page = 1;
            },
            search: function(query) {
                console.log('search', query);
            },
            build_page: function() {
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
        },
        watch: {
            page: function() {
                this.data = this.build_page();
            },
            items: function() {
                this.data = this.build_page();
            }
        }
    });

    return PageList;

});
