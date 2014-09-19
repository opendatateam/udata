/**
 * User autocompleter
 */
define(['jquery', 'api', 'form/widgets'], function($, API) {
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
                API.get('/suggest/territories', {
                    q: query,
                    size: 10
                }, function(data) {
                    data = $.map(data, function(item) {
                        item.keys = $.map(item.keys, function(value, key) {
                            return value;
                        });
                        return item
                    });
                    callback(data);
                }).fail(function() {
                    callback();
                });
            }
        });
    });

});
