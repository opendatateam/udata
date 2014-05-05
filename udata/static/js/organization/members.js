/**
 * Organization members edit page
 */
define([
    'jquery', 'notify', 'auth', 'hbs!organization/member-row', 'hbs!organization/add-member-modal',
    'x-editable', 'selectize',
], function($, Notify, Auth, row_tpl, add_modal_tpl) {
    "use strict";

    var msg_container = 'section.form .container',
        $input = $('#user-picker'),
        group_title = $('section.form').data('group-title'),
        group_id = $('section.form').data('group-id'),
        mapping = {'{org}': group_title},
        editableOpts = {
            url: window.location,
            source: [
                {value: 'admin', text: 'Administrateur'},
                {value: 'editor', text: 'Editeur'}
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
            $modal = $('#confirm-delete-modal');

        // Auth.ensure_user(Utils.i18n('login-for-members'));

        $modal.modal();
        $modal.find('.modal-footer .btn-primary').off('click').click(function() {
            $.ajax({
                url: window.location,
                type: 'DELETE',
                data: {user_id: user_id},
                success:  function(data) {
                    // var msg = Utils.i18n('member-deleted', mapping);
                    // Notify.success(msg, msg_container);
                    Notify.success('Member deleted', msg_container);
                    $row.remove();
                }
            }).error(function(e) {
                Notify.error('Error on deletion', msg_container);
                // var msg = Utils.i18n('member-error', mapping);
                // Utils.error(msg, msg_container);
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
        var $modal = $('#add-member-modal');

        // Auth.ensure_user(Utils.i18n('login-for-members'));

        $modal.find('.modal-body').html(add_modal_tpl(user));
        $modal.modal();
        $modal.find('#add-button').off('click').click(function() {
            $.post(window.location, {pk: user.id}, function(data) {
                var $row = $(row_tpl(user));
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
                $.ajax({
                    url: '/api/suggest/users',
                    type: 'GET',
                    dataType: 'json',
                    data: {
                        q: query,
                        size: 10
                    },
                    error: function() {
                        callback();
                    },
                    success: function(data) {
                        callback(data);
                    }
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
