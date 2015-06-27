/**
 * Share button
 */
define([
    'jquery',
    'i18n',
<<<<<<< HEAD:udata/static/js/widgets/share-btn.js
    'pubsub',
    'hbs!templates/widgets/share-popover'
], function($, i18n, pubsub, tpl) {
=======
    'templates/widgets/share-popover.hbs'
], function($, i18n, tpl) {
>>>>>>> Migrate dataset display page to webpack:js/widgets/share-btn.js
    'use strict';

    // Handle featured button
    $('.btn-share').each(function() {
        var $this = $(this);
        $this.popover({
            html: true,
            title: i18n._('Share'),
            placement: 'top',
            container: 'body',
            // trigger: 'focus', // Doesn't work on OSX+FF/iOS+Safari
            content: tpl({
                url: $this.data('share-url'),
                title: $this.data('share-title')
            })
        }).on('shown.bs.popover', function() {
            $(document.body).find('.share-click').each(function() {
                $(this).on('click', function(e) {
                    pubsub.publish('SHARE');
                });
            });
        });
    });

});
