/**
 * Issues button and modal
 */
import $ from 'jquery';
import log from 'logger';
import i18n from 'i18n';
import Auth from 'auth';
import API from 'api.light';
import Notify from 'notify';
import modal from 'widgets/modal';
import modalTpl from 'templates/issues/modal.hbs';
import listTpl from 'templates/issues/list.hbs';
import detailsTpl from 'templates/issues/details.hbs';
import forms from 'form/common';


// Handle featured button
$('.btn-issues').click(function(e) {
    e.preventDefault();
    const $this = $(this);
    const $modal = modal({
        title: i18n._('Issues'),
        content: modalTpl(),
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
    });
    const $title = $modal.find('.modal-title');
    const $form = $modal.find('#new-form form');
    const $newBtn = $modal.find('.btn-new');
    const $submitBtn = $modal.find('.btn-submit');
    const $backBtn = $modal.find('.btn-back');
    const $commentBtns = $modal.find('.btn-comment');
    let count = 0;

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

    function showIssue(el) {
        $(`<a href="#tab-${el.data('issue-id')}"/>`).tab('show').on('shown.bs.tab', function() {
            $backBtn.removeClass('hide');
            $newBtn.addClass('hide');
            $submitBtn.addClass('hide');
            $commentBtns.removeClass('hide');
            $title.text(el.find('h4').text());
            $modal.find('.tab-pane.active form')[0].reset();
        });
    }

    API.get($this.data('api-url'), function(data) {
        data = data.data;
        $modal.find('.spinner-container').html(listTpl({issues: data}));
        count = data.length;
        if (!data.length && Auth.user) {
            showForm();
        } else {
            for (const idx in data) {
                const issue = data[idx];
                const $tab = $(`<div class="tab-pane fade" id="tab-${issue.id}"/>`);

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
            const data = {
                type: $modal.find('input[name="type"]:checked').val(),
                title: $modal.find('#title').val(),
                comment: $modal.find('#comment').val(),
                subject: $this.data('subject')
            };

            $modal.find('button').attr('disabled', true);

            API.post($this.data('api-url'), data, function() {
                const msg = i18n._('Your issue has been sent to the team');
                Notify.success(msg);
                count++;
            }).error(function(e) {
                const msg = i18n._('An error occured while submitting your issue');
                Notify.error(msg);
                log.error(e.responseJSON);
            }).always(function() {
                $this.find('.count').text(count > 0 ? count : '');
                $modal.find('button').attr('disabled', false);
                $modal.modal('hide');
            });
        }
        return false;
    });

    // Issues details
    $modal.on('click', '.issue-list .issue', function() {
        showIssue($(this));
    });

    $commentBtns.click(function() {
        if (!Auth.need_user(i18n._('You need to be logged in to submit a comment.'))) {
            return false;
        }

        const $form = $modal.find('.tab-pane.active form');
        const close = $(this).hasClass('btn-close');

        if ($form.valid()) {
            const data = {
                comment: $form.find('#comment').val(),
                close: close,
                subject: {
                    id: $this.data('subject-id'),
                    class: $this.data('subject-class')
                }
            };

            API.post($form.attr('action'), data, function() {
                const msg = close ? i18n._('The issue has been closed') : i18n._('Your comment has been sent to the team');
                Notify.success(msg);
                if (close) {
                    count--;
                }
            }).error(function(e) {
                const msg = close ? i18n._('An error occured while closing the issue') : i18n._('An error occured while submitting your comment');
                Notify.error(msg);
                log.error(e.responseJSON);
            }).always(function() {
                $this.find('.count').text(count > 0 ? `(${count})` : '');
                $modal.modal('hide');
            });
        }
        return false;
    });
});
