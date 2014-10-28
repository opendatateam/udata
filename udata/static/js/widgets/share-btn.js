/**
 * Follow button
 */
define([
    'jquery',
    'i18n',
    'hbs!templates/widgets/share-popover'
], function($, i18n, tpl) {
    'use strict';

    // Handle featured button
    $('.btn-share').each(function() {
        var $this = $(this);
        $this.popover({
            html: true,
            title: i18n._('Share'),
            placement: 'top',
            container: 'body',
            trigger: 'focus',
            content: tpl({
                url: $this.data('share-url'),
                title: $this.data('share-title')
            })
        });
    });

});
