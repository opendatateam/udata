/**
 * Default JS module
 */
define([
    'jquery',
    'logger',
    'auth',
    'i18n',
    'api',
    'notify',
    'widgets/modal',
    'hbs!templates/organization/request-membership-modal',
    'widgets/follow-btn'
], function($, log, Auth, i18n, API, Notify, modal, modal_tpl) {

        // Async membership request
        $('a.membership').click(function() {
            var $this = $(this),
                api_url = $this.data('api');

            if (!Auth.need_user(i18n._('You need to be logged in to request membership to an organization'))) {
                return false;
            }

            var $modal = modal({
                title: i18n._("Membership request"),
                content: modal_tpl(),
                close_btn: i18n._('Cancel'),
                actions: [{
                    label: i18n._('Send request'),
                    classes: 'btn-success'
                }]
            });

            $modal.find('.btn-success').click(function() {
                var data = {comment: $modal.find('#comment').val()};
                API.post(api_url, data, function(data) {
                    var msg = i18n._('A request has been sent to the administrators');
                    Notify.success(msg);
                    $this.remove();
                    $('#pending-button').removeClass('hide');
                }).error(function(e) {
                    var msg = i18n._('Error while requesting membership');
                    Notify.error(msg);
                    console.error(e.responseJSON);
                }).always(function() {
                    $modal.modal('hide');
                });
                return false;
            });

            return false;
        });


        function displayFollowers(e) {
            e.preventDefault();
            var $parent = $(this).parent();
            $parent.siblings('.col-md-4').removeClass('hidden');
            $parent.remove();
        }
        $('.display-followers').click(displayFollowers);

    return {
        start: function() {
            log.debug('Organization display page');

            // Link tabs and history
            if (location.hash !== '') {
                $('a[href="' + location.hash + '"]').tab('show');
            }
            $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
                e.preventDefault();
                location.hash = $(e.target).attr('href').substr(1);
            });
        }
    };
});
