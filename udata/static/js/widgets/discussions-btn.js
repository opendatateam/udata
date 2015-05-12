/**
 * Follow button
 */
define(['jquery', 'api', 'auth', 'i18n', 'notify'],
function($, API, Auth, i18n, Notify) {
    'use strict';

    $('.new-discussion').click(function(e) {
        e.preventDefault();
        var $this = $(this);

        if (!Auth.need_user(i18n._('You need to be logged in to discuss.'))) {
            return false;
        }

        function displayNewDiscussionForm(el) {
            $('.list-group-form').removeClass('hidden');
        }

        function hideNewDiscussionButton(el) {
            el.addClass('hidden');
        }

        displayNewDiscussionForm($this);
        hideNewDiscussionButton($this);
    });

    $('.new-comment').click(function(e) {
        e.preventDefault();
        var $this = $(this);

        if (!Auth.need_user(i18n._('You need to be logged in to comment.'))) {
            return false;
        }

        function displayNewCommentForm(el) {
            var discussionId = $this.data('discussion-id');
            $('.list-group-form-' + discussionId).removeClass('hidden');
        }

        function hideNewCommentButton(el) {
            el.addClass('hidden');
        }

        displayNewCommentForm($this);
        hideNewCommentButton($this);
    });

    $('.open-discussion-thread').click(function(e) {
        e.preventDefault();
        var $this = $(this);

        function openDiscussionThread(el) {
            var discussionId = el.parent().data('discussion-id');
            $('.list-group-thread-' + discussionId).removeClass('hidden');
            $('.list-group-form-' + discussionId).addClass('hidden');
        }

        openDiscussionThread($this);
    });

    $('.submit-new-discussion').click(function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.parent();

        if (!Auth.need_user(i18n._('You need to be logged in to add a discussion.'))) {
            return false;
        }

        if (!$form.valid()) {
            return false;
        }

        var data = {
            title: $form.find('#title').val(),
            comment: $form.find('#comment').val()
        };

        function hideNewDiscussionForm(el, form) {
            form.addClass('hidden');
        }

        function displayNewDiscussion(el, form, data) {
            form.siblings('.list-group-item-heading').text(data.title);
            form.siblings('.list-group-item-text').text(i18n._('Discussion started today with your message.'));
            form.parent().css('height', '54px');
        }

        function submitNewDiscussion(el, form, data) {
            API.post(form.data('api-url'), data, function(data) {
                var msg = i18n._('Your comment has been sent to the server');
                Notify.success(msg);
            }).error(function(e) {
                var msg = i18n._('An error occured while submitting your comment');
                Notify.error(msg);
                console.error(e.responseJSON);
            });
        }

        hideNewDiscussionForm($this, $form);
        displayNewDiscussion($this, $form, data);
        submitNewDiscussion($this, $form, data);
    });

    $('.submit-new-comment').click(function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.parent();

        if (!Auth.need_user(i18n._('You need to be logged in to add a comment.'))) {
            return false;
        }

        if (!$form.valid()) {
            return false;
        }

        var data = {
            comment: $form.find('#comment').val()
        };

        function hideNewCommentForm(el, form) {
            form.addClass('hidden');
        }

        function displayNewComment(el, form, data) {
            var discussionId = form.parent().data('discussion-id');
            form.siblings('.list-group-item-heading').text(data.comment);
            form.siblings('.list-group-item-text').remove();
            form.parent().css('min-height', '54px');
            $('.list-group-message-number-' + discussionId).append(i18n._('and your comment!'));
        }

        function submitNewComment(el, form, data) {
            API.post(form.data('api-url'), data, function(data) {
                var msg = i18n._('Your comment has been sent to the server');
                Notify.success(msg);
            }).error(function(e) {
                var msg = i18n._('An error occured while submitting your comment');
                Notify.error(msg);
                console.error(e.responseJSON);
            });
        }

        hideNewCommentForm($this, $form);
        displayNewComment($this, $form, data);
        submitNewComment($this, $form, data);
    });

});
