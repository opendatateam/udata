import i18n from 'i18n';
import log from 'logger';
import qq from 'fine-uploader';
import allowedExtensions from 'models/allowedExtensions';

const HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob;
const _1GO = Math.pow(1024, 3);
const _1MO = Math.pow(1024, 2);
const _1KO = 1024;

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

/**
 * This is a mixin handling the fine-uploader logic.
 *
 * See the official documentation for more details:
 * http://docs.fineuploader.com/
 */
export default {
    data() {
        return {
            files: [],
            dropping: false,
            upload_endpoint: null,
            HAS_FILE_API,
        };
    },
    ready() {
        this._build_uploader();
    },

    watch: {
        upload_endpoint() {
            this._build_uploader();
        }
    },

    filters: {
        fileext(filename) {
            return filename.split('.').pop();
        },
        filesize(size) {
            if (!size || size <= 0) {
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
        _build_uploader() {
            if (!this.upload_endpoint) return;
            this.$uploader = new qq.FineUploaderBasic({
                debug: DEBUG,
                multiple: this.$options.hasOwnProperty('upload_multiple') ? this.$options.upload_multiple : true,
                uploaderType: 'basic',
                autoUpload: this.$options.hasOwnProperty('autoUpload') ? this.$options.autoUpload : true,
                button: this.$els.uploadBtn,
                request: {
                    endpoint: this.upload_endpoint,
                    inputName: 'file',
                    uuidName: 'uuid',
                    totalFileSizeName: 'size',
                    filenameParam: 'filename',
                },
                chunking: {
                    enabled: true,
                    concurrent: {
                        enabled: true
                    },
                    paramNames: {
                        chunkSize: 'chunksize',
                        partByteOffset: 'partbyteoffset',
                        partIndex: 'partindex',
                        totalParts: 'totalparts'
                    },
                    success: {
                        endpoint: this.upload_endpoint,
                    }
                },
                retry: {
                    enableAuto: true
                },
                callbacks: {
                    onUpload: this.on_upload,
                    onSubmitted: this.on_submit,
                    onProgress: this.on_progress,
                    onComplete: this.on_complete,
                    onError: this.on_error,
                },
                messages: messages,
                validation: {allowedExtensions: allowedExtensions.items}
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

        /**
         * Manually start uploading
         */
        upload(params) {
            if (params) {
                this.$uploader.setParams(params);
            }
            this.$uploader.uploadStoredFiles();
        },

        /**
         * Dispatch the file-picked event.
         *
         * See: http://docs.fineuploader.com/branch/master/api/events.html#submit
         */
        on_submit(id) {
            if (HAS_FILE_API) {
                const file = this.$uploader.getFile(id);
                file.id = id;
                file.progress = 0;
                this.files.push(file);
                this.$emit('uploader:file-submit', id, file);
            }
        },

        /**
         * Display the progress on upload started.
         *
         * See: http://docs.fineuploader.com/branch/master/api/events.html#upload
         */
        on_upload(id) {
            this.$emit('uploader:upload', id);
        },

        /**
         * Update progress bar on upload progress.
         *
         * See: http://docs.fineuploader.com/branch/master/api/events.html#progress
         */
        on_progress(id, name, uploaded, total) {
            const file = this.$uploader.getFile(id);
            file.progress = Math.round(uploaded * 100 / total);
            this.$emit('uploader:progress', id, uploaded, total);
        },

        /**
         * Dispatch a "complete" event on upload complete
         *
         * See: http://docs.fineuploader.com/branch/master/api/events.html#complete
         */
        on_complete(id, name, response) {
            if (!response.success) return;
            const file = this.$uploader.getFile(id);
            this.files.$remove(file);
            this.$emit('uploader:complete', id, response, file);
        },

        /**
         * Trigger file upload on drop complete
         *
         * See: http://docs.fineuploader.com/branch/master/features/drag-and-drop.html#processingDroppedFilesComplete
         */
        on_dropped_files_complete(files) {
            this.$uploader.addFiles(files); // this submits the dropped files to Fine Uploader
        },

        /**
         * Fine-uploader error handler
         *
         * See: http://docs.fineuploader.com/branch/master/api/events.html#error
         */
        on_error(id, name, reason, xhr) {
            // If there is a JSON message display it instead of the non-explicit default one
            if (xhr) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    reason = data.error || data.message || reason;
                } catch(e) {
                    log.error('Unable to parse error', xhr.responseText);
                }
            }
            this.$dispatch('notify', {
                type: 'error',
                icon: 'exclamation-triangle',
                title: this._('Upload error on {name}', {name}),
                details: reason,
            });
            this.$emit('uploader:error', id, name, reason);
        },

        clear() {
            this.$uploader.clearStoredFiles();
        }
    }
};
