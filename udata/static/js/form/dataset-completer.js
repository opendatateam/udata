/**
 * Dataset completer widget
 */
define([
    'jquery',
    'api',
    'hbs!templates/dataset/dropdown-item',
    'hbs!templates/dataset/card',
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
            },
            render: {
                option: function(data, escape) {
                    return itemTpl(data);
                },
                item: function(data, escape) {
                    var dataset = API.sync.get('/api/datasets/' + data.id);
                    return '<div class="card-list">'+cardTpl(dataset)+'</div>';
                }
            },
            onItemAdd: function(value, $item) {
                $item.dotdotdot();
            },
            onInitialize: function() {
                $group.find('.ellipsis-dot').dotdotdot();
            }
        });
    });

});
