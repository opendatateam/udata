/**
 * User autocompleter
 */
define(['jquery', 'form/widgets'], function($) {
    'use strict';

    $('.territory-completer').each(function() {
        var $this = $(this);

        $this.selectize({
            persist: false,
            valueField: 'id',
            labelField: 'name',
            searchField: ['name', 'code', 'keys'],
            options: $this.data('values'),
            plugins: ['remove_button'],
            load: function(query, callback) {
                if (!query.length) return callback();
                $.ajax({
                    url: '/api/suggest/territories',
                    type: 'GET',
                    dataType: 'json',
                    data: {
                        q: query,
                        size: 10
                    },
                    error: function() {
                        callback();
                    },
                    success: function(data) {
                        data = $.map(data, function(item) {
                            item.keys = $.map(item.keys, function(value, key) {
                                return value;
                            });
                            return item
                        });
                        callback(data);
                    }
                });
            }
        });
    });

});
