define([
    'jquery', 'logger', 'auth', 'i18n', 'notify'
], function($, log, Auth, i18n, Notify) {
    'use strict';

    function send_mail() {
        $.post('testmail', {}, function(data) {
            Notify.success(i18n._('Test mail sent'), '.notify-zone');
        }).error(function(e) {
            Notify.error(i18n._('An error occured while sending mail'), '.notify-zone');
            console.error(e.responseJSON);
        });
        return false;
    }

    $(function() {
        log.debug('loaded');
        $('.btn-test-mail').click(send_mail);
    });
});
