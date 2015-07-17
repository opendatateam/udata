/**
 * Dataset form
 */
define([
    'jquery',
    'widgets/modal',
    'templates/dataset/delete-resource-modal.hbs',
    'i18n',
    'logger',
    'form/common',
    'widgets/uploader',
    'form/widgets',
    'form/format-completer'
], function($, modal, tpl, i18n, log, Forms, Uploader) {

    var $form = $('form'),
        $title = $form.find('#title-id'),
        $url = $form.find('#url-id'),
        $checksum = $form.find('#checksum-value-id'),
        $checksum_group = $form.find('.checksum-group'),
        $checksum_type = $form.find('#checksum-type-id'),
        $format = $form.find('#format-id'),
        $type = $form.find('input[type=radio][name=type]'),
        $size = $form.find('#size-id'),
        $mime = $form.find('#mime-id'),
        $btn_delete = $form.find('.btn-url-delete'),
        selectize = $format[0].selectize,
        active_pane = 'file',
        values = {};

    function on_delete() {
        var $this = $(this),
            $modal = modal({
                title: i18n._('Confirm deletion'),
                content: tpl(),
                close_btn: i18n._('No'),
                actions: [{
                    label: i18n._('Yes'),
                    icon: 'fa-check',
                    classes: 'btn-warning btn-confirm'
                }]
            });

        $modal.find('.btn-confirm').click(function() {
            Forms.build($this.data('url')).submit();
        });

        return false;
    }

    function set_format(value) {
        selectize.addOption({
            value: value,
            text: value
        });
        selectize.setValue(value);
    }

    function set_pane(value) {
        clear_upload_fields();
        restore_values(value);
        switch(value) {
            case 'file':
                show_upload();
                break;
            case 'remote':
                show_remote();
                break;
            case 'api':
                show_api();
                break;
        }
        active_pane = value;
    }

    function clear_upload_fields() {
        store_values();
        $url.val(undefined);
        $checksum.val(undefined);
        $checksum_type.val(undefined);
        $mime.val(undefined);
        $size.val(undefined);

        selectize.clear();
    }

    function store_values() {
        values[active_pane] = {
            url: $url.val(),
            checksum: $checksum.val(),
            checksum_type: $checksum_type.val(),
            format: selectize.getValue(),
            size: $size.val(),
            mime: $mime.val()
        };
    }

    function restore_values(type) {
        if (type in values) {
            $url.val(values[type].url);
            $checksum.val(values[type].checksum);
            $checksum_type.val(values[type].checksum_type);
            set_format(values[type].format);
            $size.val(values[type].size);
            $mime.val(values[type].mime);
        }
    }

    function show_upload() {
        if ('file' in values && values.file.url) {
            $('.form-upload').addClass('hide');
            $('.form-upload-fields').removeClass('hide');
        } else {
            $('.form-upload-fields').addClass('hide');
            $('.form-upload').removeClass('hide');
        }
        $url.attr('readonly', 'readonly');
        $btn_delete.removeClass('hide').insertAfter($url);
        $url.parent('.input-group').find('.input-group-addon').addClass('hide').insertAfter($url);
        $checksum.attr('readonly', 'readonly');
        $checksum_type.attr('disabled', 'disabled').addClass('readonly');
        $checksum_group.removeClass('hide');
        $size.attr('readonly', 'readonly').closest('.form-group').removeClass('hide');
        $mime.attr('readonly', 'readonly').closest('.form-group').removeClass('hide');
        selectize.lock();
    }

    function show_remote() {
        $('.form-upload').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $btn_delete.addClass('hide').insertBefore($url);
        $checksum.removeAttr('readonly');
        $checksum_type.removeAttr('disabled').removeClass('readonly');
        $checksum_group.removeClass('hide');
        $size.removeAttr('readonly').closest('.form-group').removeClass('hide');
        $mime.removeAttr('readonly').closest('.form-group').removeClass('hide');
        selectize.unlock();
    }

    function show_api() {
        $('.form-upload').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $btn_delete.addClass('hide').insertBefore($url);
        $checksum_group.addClass('hide');
        $size.closest('.form-group').addClass('hide');
        $mime.closest('.form-group').addClass('hide');
        selectize.unlock();
    }

    function on_submit() {
        $checksum_type.removeAttr('disabled');
    }

    function checkUrl(e) {
        var $this = $(this);
        var $parent = $this.parent();
        var $sign = $('<span class="glyphicon form-control-feedback" aria-hidden="true"></span>');
        function populateFields(data) {
            $format.val(data['content-encoding'] || '');
            $mime.val(data['content-type'] || '');
            $size.val(data['content-length'] || '');
        }
        $.get($this.data('checkurl'), {'url': $(this).val()}
            ).done(function(data) {
                if (data.status === '200') {
                    $parent.removeClass('has-warning has-errror').addClass('has-success');
                    $parent.find('.glyphicon').remove();
                    $parent.append($sign.addClass('glyphicon-ok'));
                    populateFields(data);
                } else if (data.status == '404') {
                    $parent.removeClass('has-success has-error').addClass('has-warning');
                    $parent.find('.glyphicon').remove();
                    $parent.append($sign.addClass('glyphicon-warning-sign'));
                    populateFields({});
                }
            }).fail(function() {
                $parent.removeClass('has-warning has-success').addClass('has-error');
                $parent.find('.glyphicon').remove();
                $parent.append($sign.addClass('glyphicon-remove'));
                populateFields({});
            });
    }


    $(function() {
        $('.btn-delete').click(on_delete);

        var uploader = new Uploader('.uploader');
        $uploader = $(uploader);

        $uploader.on('complete', function(ev, name, response) {
            log.debug('complete', name, response);

            $url.val(response.url);
            $checksum.val(response.sha1);
            $size.val(response.size);
            $mime.val(response.mime);
            $checksum_type.val('sha1');

            if (!$title.val()) {
                $title.val(name);
            }

            set_format(response.format);
            store_values();
            show_upload();
        });

        $url.blur(checkUrl);

        $btn_delete.click(function() {
            uploader.clear();
            $('.form-upload-fields').addClass('hide');
            $('.form-upload').removeClass('hide');
        });

        $form.submit(on_submit);

        $type.change(function() {
            set_pane(this.value);
        });

        store_values();
        set_pane($type.filter(':checked').val());

        log.debug('Resource form loaded');
    });
});
