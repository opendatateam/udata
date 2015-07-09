define([
    'jquery',
    'class',
    'logger',
    'i18n',
    'widgets/cropper',
    'widgets/uploader',
    'widgets/modal',
    'templates/forms/image-picker-modal.hbs',
    'jquery-jcrop'
], function($, Class, log, i18n, Cropper, Uploader, modal, tpl) {
    'use strict';

    var HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob;

    var ImagePicker = Class.extend({
        init: function(el, opts) {
            this.$el = $(el);
            this.opts = opts;
            this.basename = this.$el.data('basename');

            this.$btn = this.$el.find('.image-picker-btn');
            this.$file = this.$el.find('input:file');
            this.$bbox = this.$el.find('#' + this.basename + '-bbox');
            this.$filename = this.$el.find('#' + this.basename + '-filename');
            this.$preview = this.$el.find('.image-picker-preview img');

            this.$btn.click(this.f('on_click'));
            this.endpoint = this.$el.data('endpoint');
            this.sizes = $((this.$el.data('sizes') || '100').toString().split(','))
                .map(function(idx, value) { return parseInt(value); })
                .filter(function(idx, value) { return !isNaN(value); })
                .get();

            log.info('ImagePicker initialized', this.sizes);
        },

        f: function(func) {
            return $.proxy(this[func], this);
        },

        on_click: function() {
            this.$modal = modal({
                title: i18n._('Choose an image'),
                content: tpl(),
                size: 'lg',
                close_btn: i18n._('Cancel'),
                close_cls: 'btn-warning',
                actions: [{
                    label: i18n._('Submit'),
                    icon: 'fa-check',
                    classes: 'btn-info btn-submit hide'
                }, {
                    label: i18n._('Clear'),
                    icon: 'fa-trash',
                    classes: 'btn-info btn-danger btn-clear pull-right hide'
                }]
            });

            this.$btn_submit = this.$modal.find('.btn-submit');
            this.$btn_clear = this.$modal.find('.btn-clear');

            this.uploader = new Uploader(this.$modal.find('.uploader'), {
                endpoint: this.endpoint,
                auto: false
            });
            this.$cropper = this.$modal.find('.image-cropper-container')

            $(this.uploader)
                .on('file-picked', this.f('on_file_picked'))
                .on('complete', this.f('on_upload_complete'));

            this.$btn_clear.click(this.f('clear'));
            this.$btn_submit.click(this.f('on_submit'));

            return false;
        },

        crop: function(image) {
            this.$modal.find('section').addClass('hide');
            this.$btn_submit.removeClass('hide');
            this.$btn_clear.removeClass('hide');
            this.$modal.find('.modal-title').text(i18n._('Crop your thumbnail'));
            this.$cropper.removeClass('hide');

            this.cropper = new Cropper(this.$cropper, {
                sizes: this.sizes
            });

            this.cropper.load(image);
        },

        clear: function() {
            this.$modal.find('.image-cropper-container').addClass('hide');
            this.$modal.find('.uploader').removeClass('hide');
            this.uploader.clear();
        },

        on_file_picked: function(ev, file, name) {
            if (HAS_FILE_API) {
                this.crop(URL.createObjectURL(file));
            } else {
                log.warning('File APIs not supported');
                this.uploader.upload();
            }
        },

        on_upload_complete: function(ev, name, response) {
            this.filename = response.filename;
            this.tmp_url = response.url;
            if (HAS_FILE_API) {
                this.save();
            } else {
                this.crop(response.url);
            }
        },

        on_submit: function() {
            if (HAS_FILE_API) {
                this.uploader.upload();
            } else {
                this.save()
            }
        },

        save: function() {
            this.$modal.modal('hide');
            this.$bbox.val(this.cropper.get_bbox());
            this.$filename.val(this.filename);
            this.$preview.attr('src', this.tmp_url);
        }

    });


    $('.image-picker-field').each(function() {
        new ImagePicker(this);
    });
});
