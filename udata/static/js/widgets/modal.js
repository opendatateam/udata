/**
 * A dynamic modal window
 */
define([
    'jquery',
    'hbs!templates/bs-modal',
    'i18n'
], function($, template, i18n) {

    var DEFAULTS = {
        title: null,
        content: null,
        close_btn: i18n._('Close'),
        actions: null
    };

    return function(options) {
        var el = template($.extend({}, DEFAULTS, options)),
            $modal = $(el).modal();
        return $modal;
    };

});
