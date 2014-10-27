/**
 * Dataset form
 */
define([
    'jquery',
    'widgets/modal',
    'hbs!templates/dataset/delete-resource-modal',
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
        $checksum = $form.find('#checksum-id'),
        $checksum_group = $checksum.closest('.form-group'),
        $format = $form.find('#format-id'),
        $type = $form.find('input[type=radio][name=type]'),
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

    function clear_upload_fields() {
        store_values();
        $url.val(function() {
            return this.defaultValue;
        });

        $checksum.val(function() {
            return this.defaultValue;
        });

        selectize.clear();
    }

    function store_values() {
        values[active_pane] = {
            url: $url.val(),
            checksum: $checksum.val(),
            format: selectize.getValue()
        }
    }

    function restore_values(type) {
        if (type in values) {
            $url.val(values[type].url);
            $checksum.val(values[type].checksum);
            set_format(values[type].format);
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
        $url.parent('.input-group').find('.input-group-btn').removeClass('hide').insertAfter($url);
        $url.parent('.input-group').find('.input-group-addon').addClass('hide').insertAfter($url);
        $checksum.attr('readonly', 'readonly');
        $checksum_group.removeClass('hide');
        selectize.lock();
    }

    function show_remote() {
        $('.form-upload').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $url.parent('.input-group').find('.input-group-btn').addClass('hide').insertBefore($url);
        $checksum.removeAttr('readonly');
        $checksum_group.removeClass('hide');
        selectize.unlock();
    }

    function show_api() {
        $('.form-upload').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $url.parent('.input-group').find('.input-group-btn').addClass('hide').insertBefore($url);
        $checksum_group.addClass('hide');
        selectize.unlock();
    }


    return {
        start: function() {
            $('.btn-delete').click(on_delete);

            var uploader = new Uploader('.uploader', {
                endpoint: 'upload'
            });
            $uploader = $(uploader);

            $uploader.on('complete', function(ev, id, name, response) {
                log.debug('complete', id, name, response);

                $url.val(response.url);
                $checksum.val(response.sha1);

                if (!$title.val()) {
                    $title.val(name);
                }

                set_format(response.format);
                store_values();
                show_upload();
            });

            $type.change(function() {
                clear_upload_fields();
                restore_values(this.value);
                switch(this.value) {
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
                active_pane = this.value;
            });

            log.debug('Resource form loaded');
        }
    }
});
