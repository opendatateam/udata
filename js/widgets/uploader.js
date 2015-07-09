define([
    'jquery',
    'class',
    'logger',
    'i18n',
    'fineuploader'
], function($, Class, log, i18n) {
    'use strict';

    var HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob,
        DEFAULTS = {
            endpoint: null,
            dropzones: null,
            auto: true,
        };

    var Uploader = Class.extend({
        init: function(el, options) {
            this.$el = $(el);
            this.options = $.extend({}, DEFAULTS, options);

            this.$drop = this.$el.find('.drop-pane');
            this.$btn = this.$drop.find('.btn-file');

            this.$progress = this.$el.find('.progress-pane');
            this.$progress_bar = this.$progress.find('.progress-bar')

            this.$uploader = this.$btn.fineUploader({
                debug: DEBUG,
                multiple: false,
                uploaderType: 'basic',
                autoUpload: this.options.auto,
                button: this.$btn,
                request: {
                    endpoint: this.options.endpoint || this.$el.data('endpoint'),
                    inputName: 'file',
                    customHeaders: {
                        'X-CSRFToken': $('meta[name=csrf-token]').attr('content')
                    }
                }
            });

            this.connect(this.$uploader, {
                'submit': 'on_submit',
                'upload': 'on_upload',
                'progress': 'on_progress',
                'complete': 'on_complete'
            });

            this.$dnd = this.$drop.fineUploaderDnd({
                classes: {
                    dropActive: 'drop-active'
                }
            });

            this.connect(this.$dnd, {
                'processingDroppedFiles': 'on_dropped_files',
                'processingDroppedFilesComplete': 'on_dropped_files_complete'
            });

            log.info('Uploader initialized');
        },

        connect: function($el, specs) {
            for (var event in specs) {
                $el.on(event, this.f(specs[event]));
            }
        },

        f: function(func) {
            return $.proxy(this[func], this);
        },

        /**
         * Manually start uploading
         */
        upload: function() {
            this.$uploader.fineUploader('uploadStoredFiles');
        },

        /**
         * Dispatch the file-picked event.
         */
        on_submit: function(ev, id, name) {
            var file;
            if (HAS_FILE_API) {
                file = this.$uploader.fineUploader('getFile', id);
            }
            $(this).trigger('file-picked', file, name);
        },

        /**
         * Display the progress on upload started.
         */
        on_upload: function(ev, name) {
            this.set_progress(null, name);
        },

        /**
         * Update progress bar on upload progress.
         */
        on_progress: function(event, id, name, uploaded, total) {
            var percent = Math.round(uploaded * 100 / total);
            this.set_progress(percent, name)
        },

        /**
         * Dispatch a "complete" event on upload complete
         */
        on_complete: function(event, id, name, response, xhr) {
            $(this).trigger('complete', [name, response]);
        },

        /**
         * Enable the progress on file drop
         */
        on_dropped_files: function(event) {
            this.set_progress();
        },

        /**
         * Trigger file upload on drop complete
         */
        on_dropped_files_complete: function(event, files, target) {
            //TODO: hide spinner/processing graphic
            log.debug('dropped done', files, target);
            this.$uploader.fineUploader('addFiles', files); //this submits the dropped files to Fine Uploader
        },

        set_progress: function(percent, label) {
            this.$drop.addClass('hide');
            this.$progress.removeClass('hide');

            if (percent) {
                var text = (label ? label + ' - ' : '') + percent + '%';
                this.$progress_bar
                    .text(text)
                    .css('width', percent + '%')
                    .removeClass('progress-bar-striped active')
                    .attr('aria-valuenow', percent);
            } else {
                this.$progress_bar
                    .text(label || '')
                    .css('width', '100%')
                    .addClass('progress-bar-striped active');
            }
        },

        clear: function() {
            this.$progress.addClass('hide');
            this.$drop.removeClass('hide');
            this.$uploader.fineUploader('clearStoredFiles');
        }

    });


    return Uploader;
});
