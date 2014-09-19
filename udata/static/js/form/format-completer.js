/**
 * File format autocompleter widget
 */
define(['jquery', 'api', 'form/widgets'], function($, API) {
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
                API.get('/suggest/formats', {
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
