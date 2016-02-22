/**
 * User notification module
 */
import config from 'config';
import message_template from 'templates/notification.hbs';

function show_message(message, type, container) {
    const parent = document.querySelector(container || config.notify_in);
    const child = parent.firstChild;

    const content = message_template({
        level: type == 'error' ? 'danger' : type,
        message: message
    });
    parent.insertAdjacentHTML('afterbegin', content);
}

export function error(message, container) {
    show_message(message, 'error', container);
}

export function success(message, container) {
    show_message(message, 'success', container);
}
