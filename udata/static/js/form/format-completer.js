/**
 * File format autocompleter widget
 */
define(['jquery', 'form/widgets'], function($) {
    'use strict';

    $('.format-completer').each(function() {
        var $this = $(this);

        $this.selectize({
            maxItems: 1,
            persist: false,
            valueField: 'text',
            create: function(input) {
                return {
                    value: input,
                    text: input
                }
            },
            load: function(query, callback) {
                if (!query.length) return callback();
                $.ajax({
                    url: '/api/suggest/formats',
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
                        callback(data);
                    }
                });
            }
        });
    });

});
