/**
 * Tag autocompleter widget
 */
define(['jquery', 'selectize'], function($) {
    'use strict';

    $('.tag-completer').each(function() {
        var $this = $(this),
            minlength = parseInt($this.data('tag-minlength')),
            maxlength = parseInt($this.data('tag-maxlength'));

        $this.selectize({
            // delimiter: ',',
            persist: false,
            valueField: 'text',
            plugins: ['remove_button'],
            create: function(input) {
                return {
                    value: input,
                    text: input
                }
            },
            load: function(query, callback) {
                if (!query.length) return callback();
                $.ajax({
                    url: '/api/suggest/tags',
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
