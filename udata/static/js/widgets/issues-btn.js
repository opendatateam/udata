/**
 * Issues button and modal
 */
define([
    'jquery',
    'api',
    'auth',
    'i18n',
    'notify',
    'widgets/modal',
    'hbs!templates/issues/modal',
    'hbs!templates/issues/list',
    'hbs!templates/issues/details',
    'form/common'
], function($, API, Auth, i18n, Notify, modal, modalTpl, listTpl, detailsTpl, forms) {
    'use strict';

    // Handle featured button
    $('.btn-issues').click(function() {
        var $this = $(this),
            $modal = modal({
                title: i18n._('Issues'),
                content: modalTpl({labels: forms.issues_labels}),
                actions: [{
                    label: i18n._('New issue'),
                    icon: 'fa-plus',
                    classes: 'btn-primary btn-new'
                }, {
                    label: i18n._('Submit'),
                    icon: 'fa-check',
                    classes: 'btn-info btn-submit hide'
                }, {
                    label: i18n._('Comment'),
                    icon: 'fa-comment',
                    classes: 'btn-primary btn-comment hide'
                }, {
                    label: i18n._('Comment and close'),
                    icon: 'fa-comments-o',
                    classes: 'btn-primary btn-comment btn-close hide'
                }, {
                    label: i18n._('Back'),
                    icon: 'fa-step-backward',
                    classes: 'btn-info btn-back hide'
                }]
            }),
            $title = $modal.find('.modal-title'),
            $form= $modal.find('#new-form form'),
            $newBtn = $modal.find('.btn-new'),
            $submitBtn = $modal.find('.btn-submit'),
            $backBtn = $modal.find('.btn-back'),
            $commentBtns = $modal.find('.btn-comment'),
            count = 0;

        $form.validate(forms.rules);

        function showForm() {
            $form[0].reset();
            $('<a href="#new-form"/>').tab('show').on('shown.bs.tab', function() {
                $newBtn.addClass('hide');
                $submitBtn.removeClass('hide');
                $backBtn.removeClass('hide');
                $commentBtns.addClass('hide');
                $title.text(i18n._('New issue'));
            });
        }

        API.get($this.data('api-url'), function(data) {
            data = data.data;
            $modal.find('.spinner-container').html(listTpl({issues: data, labels: forms.issues_labels}));
            count = data.length;
            if (!data.length && Auth.user) {
                showForm();
            } else {
                for (var idx in data) {
                    var issue = data[idx],
                        $tab = $('<div class="tab-pane fade" id="tab-'+ issue.id +'"/>');

                    $tab.append(detailsTpl({issue: issue}));
                    $tab.find('form').validate(forms.rules);
                    $modal.find('.tab-content').append($tab);
                }
            }
        });

        $backBtn.click(function() {
            $('<a href="#list"/>').tab('show').on('shown.bs.tab', function() {
                $newBtn.removeClass('hide');
                $submitBtn.addClass('hide');
                $backBtn.addClass('hide');
                $commentBtns.addClass('hide');
                $title.text(i18n._('Issues'));
            });
        });

        $newBtn.click(showForm);

        $submitBtn.click(function() {
            if (!Auth.need_user(i18n._('You need to be logged in to submit a new issue.'))) {
                return false;
            }

            if ($form.valid()) {
                var data = {
                    type: $modal.find('input[name="type"]:checked').val(),
                    title: $modal.find('#title').val(),
                    comment: $modal.find('#comment').val()
                };

                API.post($this.data('api-url'), data, function(data) {
                    var msg = i18n._('Your issue has been sent to the team');
                    Notify.success(msg);
                    count++;
                }).error(function(e) {
                    var msg = i18n._('An error occured while submitting your issue');
                    Notify.error(msg);
                    console.error(e.responseJSON);
                }).always(function() {
                    $this.find('.count').text(count > 0 ? count : '');
                    $modal.modal('hide');
                });
            }
            return false;
        });

        // Issues details
        $modal.on('click', '.issue-list .issue', function() {
            var $this = $(this);
            $('<a href="#tab-'+ $this.data('issue-id') +'"/>').tab('show').on('shown.bs.tab', function() {
                $backBtn.removeClass('hide');
                $newBtn.addClass('hide');
                $submitBtn.addClass('hide');
                $commentBtns.removeClass('hide');
                // $closeBtn.removeClass('hide');
                $title.text($this.find('h4').text());
                $modal.find('.tab-pane.active form')[0].reset();
            });
        });

        $commentBtns.click(function() {
            if (!Auth.need_user(i18n._('You need to be logged in to submit a comment.'))) {
                return false;
            }

            var $form = $modal.find('.tab-pane.active form'),
                close = $(this).hasClass('btn-close');

            if ($form.valid()) {
                var data = {
                    comment: $form.find('#comment').val(),
                    close: close
                };

                API.post($form.attr('action'), data, function(data) {
                    var msg = close ? i18n._('The issue has been closed') : i18n._('Your comment has been sent to the team');
                    Notify.success(msg);
                    if (close) {
                        count--;
                    }
                }).error(function(e) {
                    var msg = close ? i18n._('An error occured while closing the issue') : i18n._('An error occured while submitting your comment');
                    Notify.error(msg);
                    console.error(e.responseJSON);
                }).always(function() {
                    $this.find('.count').text(count > 0 ? '('+count+')' : '');
                    $modal.modal('hide');
                });
            }
            return false;
        });
    });

});
