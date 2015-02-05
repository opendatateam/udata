/**
 * Tag autocompleter widget
 */
define(['jquery', 'api', 'form/widgets'], function($, API) {
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
                API.get('/tags/suggest/', {
                    q: query,
                    size: 10
                }, function(data) {
                    callback(data);
                }).fail(function() {
                    callback();
                });
            }
        });
    });

});
