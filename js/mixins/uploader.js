define(['api', 'exports?qq!fineuploader', 'i18n'], function(API, qq, i18n) {
    'use strict';

    var HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob,
        _1GO = Math.pow(1024, 3),
        _1MO = Math.pow(1024, 2),
        _1KO = 1024;

    // Passthru interpolation
    const interpolation = {defaultVariables: {
        file: '{file}',
        minSizeLimit: '{minSizeLimit}',
        sizeLimit: '{sizeLimit}',
        netItems: '{netItems}',
        itemLimit: '{itemLimit}',
        extensions: '{extensions}',
    }};
    const messages = {
        emptyError: i18n._('{file} is empty, please select files again without it.', {interpolation: interpolation}),
        maxHeightImageError: i18n._('Image is too tall.'),
        maxWidthImageError: i18n._('Image is too wide.'),
        minHeightImageError: i18n._('Image is not tall enough.'),
        minWidthImageError: i18n._('Image is not wide enough.'),
        minSizeError: i18n._('{file} is too small, minimum file size is {minSizeLimit}.', {interpolation: interpolation}),
        noFilesError: i18n._('No files to upload.'),
        onLeave: i18n._('The files are being uploaded, if you leave now the upload will be canceled.'),
        retryFailTooManyItemsError: i18n._('Retry failed - you have reached your file limit.'),
        sizeError: i18n._('{file} is too large, maximum file size is {sizeLimit}.', {interpolation: interpolation}),
        tooManyItemsError: i18n._('Too many items ({netItems}) would be uploaded. Item limit is {itemLimit}.', {interpolation: interpolation}),
        typeError: i18n._('{file} has an invalid extension. Valid extension(s): {extensions}.', {interpolation: interpolation}),
        unsupportedBrowserIos8Safari: i18n._('Unrecoverable error - this browser does not permit file uploading of any kind due to serious bugs in iOS8 Safari. Please use iOS8 Chrome until Apple fixes these issues.'),
    };

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
                button: this.$els.uploadBtn,
                request: {
                    endpoint: this.upload_endpoint,
                    inputName: 'file'
                },
                callbacks: {
                    onUpload: this.on_upload,
                    onSubmitted: this.on_submit,
                    onProgress: this.on_progress,
                    onComplete: this.on_complete,
                    onError: this.on_error,
                },
                messages: messages,
                validation: {
                    allowedExtensions: [
                        // Base
                        'csv', 'txt', 'json', 'pdf', 'xml', 'rdf', 'rtf',
                        // OpenOffice
                        'ods', 'odt', 'odp', 'odg',
                        // Microsoft Office
                        'xls', 'xlsx', 'doc', 'docx', 'pps', 'ppt',
                        // Archives
                        'tar', 'gz', 'tgz', 'rar', 'zip', '7z', 'xz', 'bz2',
                        // Images
                        'jpeg', 'jpg', 'jpe', 'gif', 'png', 'dwg', 'svg', 'tiff', 'ecw', 'svgz',
                        // Geo
                        'shp', 'kml', 'kmz', 'gpx', 'shx', 'ovr',
                        // Misc
                        'dbf', 'prj', 'sql', 'epub', 'sbn', 'sbx', 'cpg', 'lyr', 'xsd', 'owl'
                    ]
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

            on_error: function(id, name, reason, xhrOrXdr) {
                this.$dispatch('notify', {
                    type: 'error',
                    icon: 'exclamation-triangle',
                    title: this._('Upload error on {name}', {name}),
                    details: reason,
                });
                this.$emit('uploader:error', id, name, reason);
            },

            clear: function() {
                // this.$progress.addClass('hide');
                // this.$drop.removeClass('hide');
                this.$uploader.clearStoredFiles();
            }
        }
    };
});
