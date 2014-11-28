/**
 * Extras fields form handling
 */
define([
    'jquery',
    'i18n',
    'auth',
    'notify',
    'widgets/modal',
    'hbs!templates/forms/extra-row',
    'hbs!templates/forms/confirm-delete-extra',
    'logger',
    'x-editable'
], function($, i18n, Auth, Notify, modal, row_tpl, confirm_tpl, Log) {
    "use strict";

    var editableKeyOpts = {
            send: 'always',
            url: window.location,
            params: function(params) {
                var value = $(this).closest('tr.extra').find('a.value').text();
                return {
                    key: params.value,
                    old_key: params.pk,
                    value: $.trim(value),
                }
            },
            success: function(response, value) {
                $(this).data('pk', value);
                $(this).closest('tr.extra').find('a.value').data('pk', value);
            }
        },
        editableValueOpts = {
            send: 'always',
            url: window.location,
            params: function(params) {
                return {
                    key: params.pk,
                    value: params.value
                }
            }
        };

    function extra_remove_handler() {
        var $this = $(this),
            $row = $this.closest('tr'),
            key = $.trim($row.find('a.key').text()),
            $modal = $('#confirm-delete-modal');

        if (!Auth.need_user(i18n._('You need to be authenticated to edit additional informations'))) {
            return false;
        }

        $modal = modal({
            title: i18n._('Confirm deletion'),
            content: confirm_tpl(),
            actions: [{
                label: i18n._('Yes'),
                // url: $this.property('url').value(),
                classes: 'btn-primary'
            }]
        });

        $modal.find('.modal-footer .btn-primary').off('click').click(function() {
            $.ajax({
                url: window.location + encodeURIComponent(key) + '/',
                type: 'DELETE',
                success:  function(data) {
                    var msg = i18n._('The additional information has been deleted');
                    Notify.success(msg);
                    $row.remove();
                }
            }).error(function(e) {
                var msg = i18n._('An error occured while editing additional informations');
                Notify.error(msg);
                console.error(e.responseJSON);
            }).always(function() {
                $modal.modal('hide');
            });
            return false;
        });

        return false;
    }


    $(function() {

        $('tr.extra a.key').editable(editableKeyOpts);
        $('tr.extra a.value').editable(editableValueOpts);

        $('a.extra-add').click(function() {
            var $row = $(this).closest('tr'),
                key = $.trim($row.find('#new-key').val()),
                value = $.trim($row.find('#new-value').val()),
                data = {key: key, value: value};

            if (!key || !value) {
                return;
            }

            if (!Auth.need_user(i18n._('You need to be authenticated to edit additional informations'))) {
                return false;
            }

            $.post(window.location, data, function(data) {
                var $row = $(row_tpl(data));
                $row.appendTo('.extras-table tbody');
                $row.find('a.key').editable(editableKeyOpts);
                $row.find('a.value').editable(editableValueOpts);
                $row.find('a.extra-remove').click(extra_remove_handler);
            }).error(function(e) {
                var msg = i18n._('An error occured while editing additional informations');
                Notify.error(msg);
                console.error(e.responseJSON);
            }).always(function() {
                $row.find('input').val('');
            });
            return false;
        });

        $('a.extra-remove').click(extra_remove_handler);
    });
});
