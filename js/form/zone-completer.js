/**
 * User autocompleter
 */
define(['jquery', 'api', 'form/widgets'], function($, API) {
    'use strict';

    var levels = {};

    API.get('spatial/levels', function(data) {
        levels = data;
    });

    function levelLabel(zone) {
        return levels.filter(function(level) {
            return level.id == zone.level;
        })[0].name;
    }

    $('.zone-completer').each(function() {
        var $this = $(this);

        $this.selectize({
            persist: false,
            valueField: 'id',
            labelField: 'name',
            searchField: ['name', 'code', 'extraKeys'],
            options: $this.data('values'),
            plugins: ['remove_button'],
            load: function(query, callback) {
                if (!query.length) return callback();
                API.get('/spatial/zones/suggest', {
                    q: query,
                    size: 10
                }, function(data) {
                    data = $.map(data, function(item) {
                        item.extraKeys = Object.keys(item.keys).map(function(key) {
                            return item.keys[key];
                        });
                        return item;
                    });
                    callback(data);
                }).fail(function() {
                    callback();
                });
            },
            render: {
                option: function(data, escape) {
                    var opt = [
                            '<div class="selectize-zone">',
                            '<span class="title">',
                            '<span class="name">',
                            escape(data.name),
                            '</span>',
                            '<span class="code">',
                            escape(data.code),
                            '</span>',
                            '</span>',
                            '<span class="level">',
                            levelLabel(data),
                            '</span>'
                        ];
                    if (data.keys) {
                        opt.push('<ul>');
                        Object.keys(data.keys).map(function(key) {
                            opt.push('<li><span class="text-uppercase">');
                            opt.push(escape(key));
                            opt.push('</span>: <span class="value">');
                            opt.push(escape(data.keys[key]));
                            opt.push('</span></li>');
                        })
                        opt.push('</ul>');
                    }
                    opt.push('</div>');
                    return opt.join('');
                },
                item: function(data, escape) {
                    return [
                        '<div class="selectize-zone-item">',
                        escape(data.name),
                        ' <span class="code">(',
                        escape(data.code),
                        ')</span></div>'
                    ].join('');
                }
            }
        });
    });

});
