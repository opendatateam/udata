/**
 * Share button
 */
import $ from 'jquery';
import i18n from 'i18n';
import pubsub from 'pubsub';
import tpl from 'templates/widgets/share-popover.hbs';

// Handle share button
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
