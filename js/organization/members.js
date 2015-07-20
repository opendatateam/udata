/**
 * Organization members edit page
 */
define([
    'jquery',
    'api',
    'notify',
    'auth',
    'i18n',
    'widgets/modal',
    'templates/organization/member-row.hbs',
    'templates/organization/add-member-modal.hbs',
    'templates/organization/remove-member-modal.hbs',
    'form/widgets',
    'x-editable'
], function($, API, Notify, Auth, i18n, modal, row_tpl, add_modal_tpl, remove_modal_tpl) {
    "use strict";

    var msg_container = 'section.form .container',
        $input = $('#user-picker'),
        editableOpts = {
            url: window.location,
            type: 'select',
            source: [
                {value: 'admin', text: i18n._('Administrator')},
                {value: 'editor', text: i18n._('Editor')}
            ]
        };

    function toggleEmpty() {
        if ($('tr.member').length > 0) {
            $('.empty').addClass('hide');
        } else {
            $('.empty').removeClass('hide');
        }
    }

    function member_remove_handler() {
        var $this = $(this),
            $row = $this.closest('tr'),
            user_id = $row.data('userid'),
            fullname = $row.find('.user-fullname').text(),
            user_url = $row.find('.user-fullname').attr('href'),
            avatar_url = $row.find('.avatar img').attr('src'),
            $modal = modal({
                title: i18n._('Confirm deletion'),
                content: remove_modal_tpl({
                    avatar_url: avatar_url,
                    fullname: fullname,
                    user_url: user_url
                }),
                close_btn: i18n._('No'),
                actions: [{
                    label: i18n._('Yes'),
                    icon: 'fa-check',
                    classes: 'btn-primary'
                }]
            });

        // Auth.ensure_user(Utils.i18n('login-for-members'));

        $modal.find('.modal-footer .btn-primary').click(function() {
            $.ajax({
                url: window.location,
                type: 'DELETE',
                data: {user_id: user_id},
                success:  function(data) {
                    Notify.success('Member deleted', msg_container);
                    $row.remove();
                }
            }).error(function(e) {
                Notify.error('Error on deletion', msg_container);
                console.error(e.responseJSON);
            }).always(function() {
                toggleEmpty();
                $modal.modal('hide');
            });
            return false;
        });

        return false;
    }

    function add_member(user) {
        var $modal = modal({
            title: i18n._('Add member'),
            content: add_modal_tpl(user),
            close_btn: i18n._('Cancel'),
            actions: [{
                label: i18n._('Add'),
                classes: 'btn-primary'
            }]
        });

        $modal.find('.btn-primary').off('click').click(function() {
            $.post(window.location, {pk: user.id}, function(data) {
                var $row = $(row_tpl(user));
                console.log(data);
                $('tr.empty').before($row);
                $row.find('.member-role').editable(editableOpts);
                $row.find('.member-remove').click(member_remove_handler);
            }).error(function(e) {
                Notify.error('Error when adding user', msg_container);
                // var msg = Utils.i18n('member-error', mapping);
                // Notify.error(msg, msg_container);
                console.error(e.responseJSON);
            }).always(function() {
                toggleEmpty();
                $modal.modal('hide');
            });
            return false;
        });

        return false;
    }


    $(function() {

        $('.member-role').editable(editableOpts);

        $input.selectize({
            persist: false,
            valueField: 'id',
            labelField: 'fullname',
            searchField: ['fullname'],
            load: function(query, callback) {
                if (!query.length) return callback();
                API.get('/users/suggest/', {
                    q: query,
                    size: 10
                }, function(data) {
                    callback(data);
                }).fail(function() {
                    callback();
                });
            },
            render: {
                item: function(item, escape) {
                    add_member(item);
                    return '';
                },
                option: function(item, escape) {
                    var avatar = item.avatar_url || '';
                    return '<div>' +
                        '<img src="' + avatar + '" width="32" height="32"/>' +
                        '<span>' + escape(item.fullname) + '</span>' +
                    '</div>';
                }
            }
        });

        $('a.member-remove').click(member_remove_handler);
    });

});
