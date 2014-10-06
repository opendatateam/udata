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
        $checksum_group = $checksum.parent('.form-group'),
        $format = $form.find('#format-id');
        selectize = $format[0].selectize;

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
        $url.val(function() {
            return this.defaultValue;
        });

        $checksum.val(function() {
            return this.defaultValue;
        });

        console.log('Initial value', $format[0].defaultValue);
        set_format($format[0].defaultValue);
    }

    function show_upload() {
        $('.form-upload-fields, .form-upload-progress').addClass('hide');
        $('.form-upload').removeClass('hide');
        $url.attr('readonly', 'readonly');
        $url.parent('.input-group').find('.input-group-btn').removeClass('hide').insertAfter($url);
        $url.parent('.input-group').find('.input-group-addon').addClass('hide').insertAfter($url);
        $checksum.attr('readonly', 'readonly');
        $checksum_group.removeClass('hide');
        selectize.disable();
    }

    function show_remote() {
        $('.form-upload, .form-upload-progress').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $url.parent('.input-group').find('.input-group-btn').addClass('hide').insertBefore($url);
        $checksum.removeAttr('readonly');
        $checksum_group.removeClass('hide');
        selectize.enable();
    }

    function show_api() {
        $('.form-upload, .form-upload-progress').addClass('hide');
        $('.form-upload-fields').removeClass('hide');
        $url.removeAttr('readonly');
        $url.parent('.input-group').find('.input-group-addon').removeClass('hide').insertBefore($url);
        $url.parent('.input-group').find('.input-group-btn').addClass('hide').insertBefore($url);
        $checksum_group.addClass('hide');
        selectize.enable();
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

                this.$progress.addClass('hide');

                $('.form-upload-fields').removeClass('hide');
                $url.val(response.url);
                $checksum.val(response.sha1);

                if (!$title.val()) {
                    $title.val(name);
                }

                set_format(response.format);
                selectize.disable();
                file_loaded = true;
            });

            $('input[type=radio][name=type]').change(function() {
                clear_upload_fields();
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
            });

            log.debug('Resource form loaded');
        }
    }
});
