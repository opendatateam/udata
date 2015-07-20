/**
 * Dataset completer widget
 */
define([
    'jquery',
    'api',
    'templates/dataset/dropdown-item.hbs',
    'templates/dataset/card.hbs',
    'form/widgets'
], function($, API, itemTpl, cardTpl) {
    'use strict';

    $('.dataset-completer').each(function() {
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
                API.get('/datasets/suggest/', {
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
                    var dataset = API.sync.get('/datasets/' + data.id);
                    return '<div class="card-input">'+cardTpl(dataset)+'</div>';
                }
            }
        });
    });

});
