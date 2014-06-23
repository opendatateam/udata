/**
 * Membership requests specific features
 */
define([
    'jquery',
    'i18n',
    'notify',
    'auth',
    'widgets/modal',
    'hbs!templates/organization/refuse-membership-modal',
    'form/common'
], function($, i18n, Notify, Auth, modal, refusal_tpl, forms) {
    "use strict";

    $('a.membership-accept').click(function() {
        var $this = $(this),
            api_url = $this.data('api');

        // Auth.need_user(i18n('login-for-pending'));

        $.post(api_url, {}, function(data) {
            var msg = i18n._('Membership request has been accepted');
            Notify.success(msg);
            $this.closest('.pending-request').remove();
            if ($('.pending-request').length == 0) {
                $('.empty').removeClass('hide');
            }
        }).error(function(e) {
            var msg = i18n._('Error while responding to membership request');
            Notify.error(msg);
            console.error(e.responseJSON);
        });

        return false;
    });

    $('a.membership-refuse').click(function() {
        var $this = $(this),
            api_url = $this.data('api'),
            $modal = modal({
                title: i18n._("Membership refusal"),
                content: refusal_tpl(),
                close_btn: i18n._('Cancel'),
                actions: [{
                    label: i18n._('Refuse'),
                    classes: 'btn-primary'
                }]
            });

        // Auth.need_user(Utils.i18n('login-for-pending'));

        $modal.find('form').validate(forms.rules);
        $modal.find('.modal-footer .btn-primary').off('click').click(function() {
            if ($modal.find('form').valid()) {
                var data = {comment: $modal.find('#comment').val()};
                $.post(api_url, data, function(data) {
                    var msg = i18n._('Membership request has been refused');
                    Notify.success(msg);
                    $this.closest('.pending-request').remove();
                    if ($('.pending-request').length == 0) {
                        $('.empty').removeClass('hide');
                    }
                }).error(function(e) {
                    var msg = i18n._('Error while responding to membership request');
                    Notify.error(msg);
                    console.error(e.responseJSON);
                }).always(function() {
                    $modal.modal('hide');
                });
            }
            return false;
        });

        return false;
    });

});
