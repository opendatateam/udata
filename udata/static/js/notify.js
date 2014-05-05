/**
 * User notification module
 */
define(['jquery', 'hbs!templates/notification'], function($, message_template) {
    'use strict';

    function show_message(message, type, container) {
        container = container || 'section.default .container:first';
        $(container).prepend(message_template({
            level: type == 'error' ? 'danger' : type,
            message: message
        }));
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
