/**
 * Follow button
 */
define(['jquery', 'api', 'auth', 'i18n', 'notify'],
function($, API, Auth, i18n, Notify) {
    'use strict';

    function hideNewForm(el, form) {
        form.addClass('fadeOutDown');
        setTimeout(function() {
            form.addClass('hidden');
        }, 1000);
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

    function displayNewDiscussionForm(el) {
        $('.list-group-form-discussion').removeClass('hidden').addClass('fadeInDown');
    }

    function hideNewDiscussionButton(el) {
        el.addClass('hidden');
    }

    $('.new-discussion').click(function(e) {
        e.preventDefault();
        var $this = $(this);

        if (!Auth.need_user(i18n._('You need to be logged in to discuss.'))) {
            return false;
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
            var discussionId = el.data('discussion-id');
            $('.list-group-form-' + discussionId).removeClass('hidden').addClass('fadeInDown');
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
            $('.list-group-thread-' + discussionId).removeClass('hidden').addClass('fadeInDown');
            $('.list-group-form-' + discussionId).addClass('hidden');
        }

        openDiscussionThread($this);
    });

    $('.submit-new-discussion').click(function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.parent();
        var $newMessage = $('.list-group-new-message');

        if (!Auth.need_user(i18n._('You need to be logged in to add a discussion.')) || !$form.valid()) {
            return false;
        }

        var data = {
            title: $form.find('#title').val(),
            comment: $form.find('#comment').val(),
            subject: $form.data('subject')
        };

        function displayNewDiscussion(el, form, data, newMessage) {
            form.siblings('.list-group-item-heading').text(data.title);
            form.siblings('.list-group-item-text').text(i18n._('Discussion started today with your message.'));
            form.parent().css('height', '54px');
            newMessage.addClass('fadeInDown').removeClass('hidden');
            newMessage.children('.list-group-item-heading').text(data.comment);
        }

        hideNewForm($this, $form);
        displayNewDiscussion($this, $form, data, $newMessage);
        submitNewComment($this, $form, data);
    });

    $('.submit-new-comment').click(function(e) {
        e.preventDefault();
        var $this = $(this);
        var $form = $this.parent();
        var discussionId = $form.parent().data('discussion-id');

        if (!Auth.need_user(i18n._('You need to be logged in to add a comment.')) || !$form.valid()) {
            return false;
        }

        var data = {
            comment: $form.find('#comment').val()
        };

        function displayNewComment(el, form, data) {
            form.siblings('.list-group-item-heading').text(data.comment);
            form.siblings('.list-group-item-text').remove();
            form.parent().css('min-height', '54px');
            $('.list-group-message-number-' + discussionId).append(i18n._('and your comment!'));
        }

        hideNewForm($this, $form);
        displayNewComment($this, $form, data);
        submitNewComment($this, $form, data);
    });

    $('.suggest-tag').click(function(e) {
        console.log('clicked');
        e.preventDefault();
        var $newDiscussion = $('.new-discussion');

        // Otherwise the scrollTop is not effective if the form is already
        // displayed (hence the new discussion button is hidden)
        $newDiscussion.removeClass('hidden');

        // Scroll to the new discussion thread form
        $('html, body').animate({
            scrollTop : $newDiscussion.offset().top
        }, 400);

        if (!Auth.need_user(i18n._('You need to be logged in to propose a tag.'))) {
            return false;
        }

        displayNewDiscussionForm($newDiscussion);
        hideNewDiscussionButton($newDiscussion);

        // Prefill the new discussion thread form
        $newDiscussion.parent().find('#title').val(
            i18n._('New tag suggestion to improve metadata'));
        $newDiscussion.parent().find('#comment').val(
            i18n._('Hello,\n\nI propose this new tag: '));
    });

});
