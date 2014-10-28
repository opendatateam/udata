/**
 * Follow button
 */
define([
    'jquery',
    'i18n',
    'hbs!templates/widgets/export-popover'
], function($, i18n, tpl) {
    'use strict';

    // Handle export button
    $('.export-btn').each(function() {
        var $btn = $(this),
            formats = $.map($btn.find('link[rel=alternate]'), function(link) {
                return {
                    url: $(link).attr('href'),
                    title: $(link).attr('title')
                };
            });

        $btn.popover({
            html: true,
            title: i18n._('Export'),
            container: 'body',
            trigger: 'focus',
            content: tpl({
                formats: formats
            })
        }).on('shown.bs.popover', function() {
            console.log(this);
        });
    });

});
