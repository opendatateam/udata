/**
 * Integrate button
 */
import $ from 'jquery';
import i18n from 'i18n';
import pubsub from 'pubsub';
import tpl from 'templates/widgets/integrate-popover.hbs';

// Handle integrate button
$('.btn-integrate').each(function() {
    let $this = $(this);
    $this.popover({
        html: true,
        placement: 'top',
        container: 'body',
        // trigger: 'focus', // Doesn't work on OSX+FF/iOS+Safari
        content: tpl({
            dataset_id: $this.data('dataset-id'),
            widget_url: $this.data('widget-url'),
            site_url: $this.data('site-url').slice(0, -1), // Remove the trailing slash.
            documentation_url: $this.data('documentation-url'),
            help_text: i18n._('Copy-paste this code within your own HTML at the place you want the current dataset to appear:'),
            tooltip_text: i18n._('Click the button to copy the whole code within your clipboard'),
            documentation_text: i18n._('Read the documentation to insert more than one dataset'),
        })
    }).on('shown.bs.popover', function() {
        let textarea = $(document.body).find('.integrate-content')[0];
        textarea.select();
        $(document.body).find('.integrate-click').each(function() {
            let $this = $(this);
            $this.tooltip();
            $this.on('click', function(e) {
                e.preventDefault();
                textarea.select();
                document.execCommand('copy');
                pubsub.publish('INTEGRATE');
            });
        });
    });
});
