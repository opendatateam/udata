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
                API.get('/suggest/reuses', {
                    q: query,
                    size: 10
                }, function(data) {
                    callback(data);
                }).fail(function() {
                    callback();
                });
            },
            render: {
                option: function(data, escape) {
                    return itemTpl(data);
                },
                item: function(data, escape) {
                    var reuse = API.sync.get('/reuses/' + data.id);
                    return '<div class="card-input">'+cardTpl(reuse)+'</div>';
                }
            }
        });
    });

});
