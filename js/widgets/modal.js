/**
 * A dynamic modal window
 */
define([
    'jquery',
    'templates/bs-modal.hbs',
    'i18n'
], function($, template, i18n) {

    var DEFAULTS = {
        title: null,
        content: null,
        close_btn: i18n._('Close'),
        close_icon: 'fa-times',
        close_cls: 'btn-default',
        actions: null,
        size: null
    };

    return function(options) {
        var el = template($.extend({}, DEFAULTS, options)),
            $modal = $(el).modal();

        // Single use only: modal is destroyed when hidden
        $modal.on('hidden.bs.modal', function() {
            this.remove();
        });

        return $modal;
    };

});
