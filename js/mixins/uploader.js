define(['api', 'exports?qq!fineuploader'], function(API, qq) {
    'use strict';

    var HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob,
        _1GO = Math.pow(1024, 3),
        _1MO = Math.pow(1024, 2),
        _1KO = 1024;

    return {
        data: function() {
            return {
                dropping: false,
                upload_endpoint: null,
                HAS_FILE_API: HAS_FILE_API,
                files: []
            };
        },
        ready: function() {
            this.$uploader = new qq.FineUploaderBasic({
                debug: DEBUG,
                multiple: this.$options.hasOwnProperty('upload_multiple') ? this.$options.upload_multiple : true,
                uploaderType: 'basic',
                autoUpload: this.$options.hasOwnProperty('autoUpload') ? this.$options.autoUpload : true,
                button: this.$$.uploadBtn,
                request: {
                    endpoint: this.upload_endpoint,
                    inputName: 'file'
                },
                callbacks: {
                    onUpload: this.on_upload,
                    onSubmitted: this.on_submit,
                    onProgress: this.on_progress,
                    onComplete: this.on_complete
                }
            });


            this.$dnd = new qq.DragAndDrop({
                dropZoneElements: [this.$el],
                classes: {
                    dropActive: this.$options.dropActive || 'drop-active'
                },
                callbacks: {
                  processingDroppedFilesComplete: this.on_dropped_files_complete
                }
            });
        },
        watch: {
            upload_endpoint: function(endpoint) {
                if (endpoint && this.$uploader) {
                    this.$uploader.setEndpoint(endpoint);
                }
            }
        },
        directives: {
            dropzone: {

            }
        },
        filters: {
            filesize: function(size) {
                if (size <= 0) {
                    return '-';
                }
                if (size > _1GO) {
                    return Math.round(size * 100 / _1GO) / 100 + ' Go';
                } else if (size > _1MO) {
                    return Math.round(size * 10 / _1MO) / 10 + ' Mo';
                } else if (size > _1KO) {
                    return Math.round(size * 10 / _1KO) / 10 + ' Ko';
                } else {
                    return size + ' o';
                }
            }
        },
        methods: {
            /**
             * Manually start uploading
             */
            upload: function(params) {
                if (params) {
                    this.$uploader.setParams(params);
                }
                this.$uploader.uploadStoredFiles();
            },

            /**
             * Dispatch the file-picked event.
             */
            on_submit: function(id, name) {
                var file;
                if (HAS_FILE_API) {
                    file = this.$uploader.getFile(id);
                    file.id = id;
                    file.progress = 0;
                    this.files.push(file);
                    this.$emit('uploader:file-submit', id, file);
                }
            },

            /**
             * Display the progress on upload started.
             */
            on_upload: function(id, name) {
                this.$emit('uploader:upload', id);
            },

            /**
             * Update progress bar on upload progress.
             */
            on_progress: function(id, name, uploaded, total) {
                var file = this.$uploader.getFile(id);
                file.progress = Math.round(uploaded * 100 / total);
                this.$emit('uploader:progress', id, uploaded, total);
            },

            /**
             * Dispatch a "complete" event on upload complete
             */
            on_complete: function(id, name, response, xhr) {
                var file = this.$uploader.getFile(id);
                this.files.$remove(this.files.indexOf(file));
                this.$emit('uploader:complete', id, response, file);
            },

            /**
             * Trigger file upload on drop complete
             */
            on_dropped_files_complete: function(files, target) {
                this.$uploader.addFiles(files); //this submits the dropped files to Fine Uploader
            },

            clear: function() {
                // this.$progress.addClass('hide');
                // this.$drop.removeClass('hide');
                this.$uploader.clearStoredFiles();
            }
        }
    };
});
