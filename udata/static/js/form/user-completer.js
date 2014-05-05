/**
 * User autocompleter
 */
define(['jquery', 'selectize'], function($) {
    'use strict';

    $('.user-completer').each(function() {
        var $this = $(this);

        $this.selectize({
            persist: false,
            valueField: 'id',
            labelField: 'fullname',
            searchField: ['fullname'],
            options: $this.data('values'),
            plugins: ['remove_button'],
            load: function(query, callback) {
                if (!query.length) return callback();
                $.ajax({
                    url: '/api/suggest/users',
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
                item: function(item, escape) {
                    var avatar = item.avatar_url || '';
                    return '<div>' +
                        '<img src="' + avatar + '" width="20" height="20"/>' +
                        '<span>' + escape(item.fullname) + '</span>' +
                    '</div>';
                },
                option: function(item, escape) {
                    var avatar = item.avatar_url || '';
                    return '<div>' +
                        '<img src="' + avatar + '" width="32" height="32"/>' +
                        '<span>' + escape(item.fullname) + '</span>' +
                    '</div>';
                }
            },
        });
    });

});
