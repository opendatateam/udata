/**
 * Dataset display page JS module
 */
define([
    'jquery',
    'logger',
    'i18n',
    'hbs!templates/dataset/resource-modal-body',
    'widgets/modal',
    'widgets/featured',
    'widgets/follow-btn',
    'widgets/issues-btn',
], function($, log, i18n, template, modal) {

    function prepare_resources() {
        $('.resources-list').items('http://schema.org/DataDownload').each(function() {
            var $this = $(this);

            // Prevent default click on link
            $this.find('a[itemprop="url"]').click(function(e) {
                e.preventDefault();
            })

            // Ensure toolbar links does not interfere
            $this.find('.tools a').click(function(e) {
                e.stopPropagation();
            })

            // Display detailled informations in a modal
            $this.click(function() {
                modal({
                    title: $this.property('name').value(),
                    content: template($this.microdata()[0]),
                    actions: [{
                        label: i18n._('Download'),
                        url: $this.property('url').value(),
                        classes: 'btn-success'
                    }]
                });
            });

        });

        // Hide expander on click
        $('.expander').click(function() {
            $(this).animate({height: 0, opacity: 0}, function() {
                $(this).remove();
            });
        });
    }

    return {
        start: function() {
            log.debug('Dataset display page');
            prepare_resources();
        }
    }
});
