/**
 * Discussion button
 */
import $ from 'jquery';
import log from 'logger';
import i18n from 'i18n';
import Auth from 'auth';
import API from 'api.light';
import Notify from 'notify';

function hideNewForm(el, form) {
    form.addClass('fadeOutDown');
    setTimeout(function() {
        form.addClass('hidden');
    }, 1000);
}

function submitNewComment(el, form, data, callback) {
    const $submit = form.find('button[type=submit]');
    const content = $submit.html();
    $submit.html('<span class="fa fa-refresh fa-spin"></span>');
    $submit.attr('disabled', true);
    API.post(form.data('api-url'), data, function() {
        const msg = i18n._('Your comment has been sent to the server');
        Notify.success(msg);
        $submit.html(content);
        hideNewForm(el, form);
        callback();
    }).error(function(e) {
        const msg = i18n._('An error occured while submitting your comment');
        Notify.error(msg, form[0]);
        log.error(e.responseJSON);
        $submit.html(content);
        $submit.attr('disabled', false);
    });
}

function displayNewDiscussionForm() {
    $('.list-group-form-discussion').removeClass('hidden').addClass('fadeInDown');
}

function hideNewDiscussionButton(el) {
    el.addClass('hidden');
}

$('.new-discussion').click(function(e) {
    e.preventDefault();
    const $this = $(this);

    if (!Auth.need_user(i18n._('You need to be logged in to discuss.'))) {
        return false;
    }

    displayNewDiscussionForm($this);
    hideNewDiscussionButton($this);
});

$('.new-comment').click(function(e) {
    e.preventDefault();
    const $this = $(this);

    if (!Auth.need_user(i18n._('You need to be logged in to comment.'))) {
        return false;
    }

    const discussionId = $this.data('discussion-id');
    $(`.list-group-form-${discussionId}`).removeClass('hidden').addClass('fadeInDown');
    $this.addClass('hidden');
});

$('.open-discussion-thread').click(function(e) {
    e.preventDefault();
    const discussionId = $(this).parent().data('discussion-id');
    $(`.list-group-thread-${discussionId}`).removeClass('hidden').addClass('fadeInDown');
    $(`.list-group-form-${discussionId}`).addClass('hidden');
});

$('.submit-new-discussion').click(function(e) {
    e.preventDefault();
    const $this = $(this);
    const $form = $this.parent();
    const $newMessage = $('.list-group-new-message');

    if (!Auth.need_user(i18n._('You need to be logged in to add a discussion.')) || !$form.valid()) {
        return false;
    }

    const data = {
        title: $form.find('#title-new-discussion').val(),
        comment: $form.find('#comment-new-discussion').val(),
        subject: $form.data('subject')
    };

    submitNewComment($this, $form, data, function() {
        $form.siblings('.list-group-item-heading').text(data.title);
        $form.siblings('.list-group-item-text').text(i18n._('Discussion started today with your message.'));
        $form.parent().css('height', '54px');
        $newMessage.addClass('fadeInDown').removeClass('hidden');
        $newMessage.children('.list-group-item-heading').text(data.comment);
    });
});

$('.submit-new-message').click(function(e) {
    e.preventDefault();
    const $this = $(this);
    const $form = $this.parent();
    const discussionId = $form.parent().data('discussion-id');

    if (!Auth.need_user(i18n._('You need to be logged in to add a comment.')) || !$form.valid()) {
        return false;
    }

    const data = {
        comment: $form.find('#comment-new-message').val()
    };

    submitNewComment($this, $form, data, function() {
        $form.siblings('.list-group-item-heading').text(data.comment);
        $form.siblings('.list-group-item-text').remove();
        $form.parent().css('min-height', '54px');
        $(`.list-group-message-number-${discussionId}`).append(i18n._('and your comment!'));
    });
});

$('.suggest-tag').click(function(e) {
    e.preventDefault();
    const $newDiscussion = $('.new-discussion');
    const $form = $newDiscussion.parent();

    // Otherwise the scrollTop is not effective if the form is already
    // displayed (hence the new discussion button is hidden)
    $newDiscussion.removeClass('hidden');

    // Scroll to the new discussion thread form
    $('html, body').animate({
        scrollTop: $newDiscussion.offset().top
    }, 400);

    if (!Auth.need_user(i18n._('You need to be logged in to propose a tag.'))) {
        return false;
    }

    displayNewDiscussionForm($newDiscussion);
    hideNewDiscussionButton($newDiscussion);

    // Prefill the new discussion thread form
    $form.find('#title-new-discussion').val(
        i18n._('New tag suggestion to improve metadata'));
    $form.find('#comment-new-discussion').val(
        i18n._('Hello,') + '\n\n' + i18n._('I propose this new tag: '));
});
