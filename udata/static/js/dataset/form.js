/**
 * Dataset form
 */
define([
    'jquery',
    'widgets/modal',
    'hbs!templates/dataset/delete-modal',
    'i18n',
    'logger',
    'form/common',
    'form/widgets',
    'form/date-range-picker',
    'form/tag-completer',
    'form/zone-completer'
], function($, modal, tpl, i18n, log, Forms) {
    "use strict";

    function on_delete() {
        var $this = $(this),
            $modal = modal({
                title: i18n._('Confirm deletion'),
                content: tpl(),
                close_btn: i18n._('No'),
                actions: [{
                    label: i18n._('Yes'),
                    icon: 'fa-check',
                    classes: 'btn-warning btn-confirm'
                }]
            });

        $modal.find('.btn-confirm').click(function() {
            Forms.build($this.data('url')).submit();
        });

        return false;
    }

    return {
        start: function() {
            log.debug('Dataset form page');
            $('.btn-delete').click(on_delete);
        }
    }
});
