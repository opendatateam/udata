/**
 * Dataset completer widget
 */
define(['jquery', 'form/widgets'], function($) {
    'use strict';


    $('.dataset-completer').each(function() {
        var $this = $(this);

        $this.selectize({
            persist: false,
            valueField: 'id',
            labelField: 'title',
            searchField: ['title'],
            options: $this.data('values'),
            plugins: ['remove_button'],
            load: function(query, callback) {
                if (!query.length) return callback();
                $.ajax({
                    url: '/api/suggest/datasets',
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
