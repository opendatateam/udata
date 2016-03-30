/**
 * Default JS module
 */

// ES6 environment
import 'babel-polyfill';

import $ from 'jquery';
import log from 'logger';
import Auth from 'auth';
import i18n from 'i18n';
import API from 'api.light';
import Notify from 'notify';
import modal from 'widgets/modal';
import modal_tpl from 'templates/organization/request-membership-modal.hbs';
import 'widgets/follow-btn';

// Async membership request
$('a.membership').click(function() {
    const $this = $(this);
    const api_url = $this.data('api');

    if (!Auth.need_user(i18n._('You need to be logged in to request membership to an organization'))) {
        return false;
    }

    const $modal = modal({
        title: i18n._('Membership request'),
        content: modal_tpl(),
        close_btn: i18n._('Cancel'),
        actions: [{
            label: i18n._('Send request'),
            classes: 'btn-success'
        }]
    });

    $modal.find('.btn-success').click(function() {
        const data = {comment: $modal.find('#comment').val()};
        $modal.find('button').attr('disabled', true);
        API.post(api_url, data, function() {
            const msg = i18n._('A request has been sent to the administrators');
            Notify.success(msg);
            $this.remove();
            $('#pending-button').removeClass('hide');
        }).error(function(e) {
            const msg = i18n._('Error while requesting membership');
            Notify.error(msg);
            log.error(e.responseJSON);
        }).always(function() {
            $modal.modal('hide');
            $modal.find('button').attr('disabled', false);
        });
        return false;
    });

    return false;
});


function displayFollowers(e) {
    e.preventDefault();
    const $parent = $(this).parent();
    $parent.siblings('.col-md-4').removeClass('hidden');
    $parent.remove();
}
$('.display-followers').click(displayFollowers);

function hash_to_tab() {
    // Link tabs and history
    if (location.hash !== '') {
        $(`a[href="${location.hash}"]`).tab('show');
    }
}


$(function() {
    log.debug('Organization display page');

    hash_to_tab();

    $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
        e.preventDefault();
        location.hash = $(e.target).attr('href').substr(1);
    });

    $(window).on('hashchange', hash_to_tab);

    if (location.hash === '') {
      // Open the first tab by default
      $('.nav-pills li:first-child a').tab('show');
      // But don't scroll down to it
      $(window).scrollTop(0);
    }
});
