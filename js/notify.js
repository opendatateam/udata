/**
 * User notification module
 */
define([
    'jquery',
    'logger',
    'config',
    'templates/notification.hbs'
], function($, Log, config, message_template) {
    'use strict';

    function show_message(message, type, container) {
        container = container || config.notify_in;
        $(container).prepend(message_template({
            level: type == 'error' ? 'danger' : type,
            message: message
        }));
        Log.debug('Notify:', {type: type, message: message, container: container});
    }

    return {
        error: function(message, container) {
            show_message(message, 'error', container);
        },

        success: function(message, container) {
            show_message(message, 'success', container);
        }
    };
});
