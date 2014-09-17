/**
 * Dataset completer widget
 */
define([
    'jquery',
    'api',
    'hbs!templates/reuse/dropdown-item',
    'hbs!templates/reuse/card',
    'form/widgets'
], function($, API, itemTpl, cardTpl) {
    'use strict';

    $('.reuse-completer').each(function() {
        var $this = $(this),
            $group = $this.closest('.form-group');

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
                    url: '/api/suggest/reuses',
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
            },
            render: {
                option: function(data, escape) {
                    return itemTpl(data);
                },
                item: function(data, escape) {
                    var reuse = API.sync.get('/api/reuses/' + data.id);
                    return '<div class="card-input">'+cardTpl(reuse)+'</div>';
                }
            }
        });
    });

});
