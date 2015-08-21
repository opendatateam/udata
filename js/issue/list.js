/**
 * Issues button and modal
 */
define([
    'jquery',
    'auth',
    'i18n',
    'api.light',
    'notify',
    'widgets/modal',
    'templates/issues/details.hbs',
    'form/common'
], function($, Auth, i18n, API, Notify, modal, detailsTpl, forms) {
    'use strict';

    // Handle featured button
    $('.issue').click(function() {
        var $this = $(this);

        API.get($this.data('api-url'), function(issue) {
            var $modal = modal({
                    content: detailsTpl({issue: issue}),
                    actions: [{
                        label: i18n._('Comment'),
                        icon: 'fa-comment',
                        classes: 'btn-primary btn-comment'
                    }, {
                        label: i18n._('Comment and close'),
                        icon: 'fa-comments-o',
                        classes: 'btn-primary btn-comment btn-close'
                    }]
                }),
                $form = $modal.find('form'),
                $btns = $modal.find('.btn-comment');

            $form.validate(forms.rules);

            $btns.click(function() {
                if (!Auth.need_user(i18n._('You need to be logged in to submit a comment.'))) {
                    return false;
                }

                var $form = $modal.find('form'),
                    close = $(this).hasClass('btn-close');

                if ($form.valid()) {
                    var data = {
                        comment: $form.find('#comment').val(),
                        close: close
                    };

                    API.post(issue.url, data, function(data) {
                        var msg = close ? i18n._('The issue has been closed') : i18n._('Your comment has been sent to the team');
                        Notify.success(msg);
                        if (close) {
                            $('.closed-issues').append($this);
                        }
                    }).error(function(e) {
                        var msg = close ? i18n._('An error occured while closing the issue') : i18n._('An error occured while submitting your comment');
                        Notify.error(msg);
                        console.error(e.responseJSON);
                    }).always(function() {
                        $modal.modal('hide');
                    });
                }
                return false;
            });
        });

    });

});
