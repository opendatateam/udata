/**
 * File uploader widget
 */
define(['jquery', 'bootstrap', 'jqfineuploader'], function($) {
    'use strict';

    $('.upload-btn').each(function() {
        var $this = $(this),
            $group = $this.closest('.input-group'),
            $input = $group.find('input[type="url"]'),
            $progress = $this.closest('.form-group').find('.progress'),
            $removeBtn = $this.siblings('.upload-remove-btn'),
            endpoint = $input.data('endpoint');

        $this
            .popover({
                trigger: 'hover',
                placement: 'top',
                container: 'body'
            })
            .fineUploader({
                debug: true,
                multiple: false,
                button: $this,
                uploaderType: 'basic',
                request: {
                    endpoint: endpoint,
                    inputName: 'file',
                    customHeaders: {
                        'X-CSRFToken': $('meta[name=csrf-token]').attr('content')
                    }
                }
            })
            .on('upload', function(ev, name) {
                $progress
                    .width($group.width())
                    .height($group.height())
                    .removeClass('hide');
                $group.addClass('hide');
            })
            .on('progress', function(ev, id, name, uploaded, total) {
                var percent = Math.round(uploaded * 100 / total) + '%'
                $progress.find('.progress-bar').width(percent).text(percent);
            })
            .on('complete', function(ev, id, name, response, xhr) {
                $input.val(response.url);
                $group.removeClass('hide')
                $progress.addClass('hide');

                $this.addClass('hide');
                $removeBtn.removeClass('hide').before($this);
            });

        $removeBtn.click(function() {
            $removeBtn.addClass('hide');
            $this.removeClass('hide');
            $progress.find('.progress-bar').width(0).text('0%');
        })
    });

});
