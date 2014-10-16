define([
    'jquery',
    'class',
    'logger',
    'i18n',
    'widgets/cropper',
    'widgets/uploader',
    'widgets/modal',
    'hbs!templates/forms/image-picker-modal',
    'jcrop'
], function($, Class, log, i18n, Cropper, Uploader, modal, tpl) {
    'use strict';

    var HAS_FILE_API = window.File && window.FileReader && window.FileList && window.Blob;

    var ImagePicker = Class.extend({
        init: function(el, btns) {
            this.$el = $(el);
            this.$btns = $(btns);

            this.$btns.click(this.f('on_click'));
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

            var uploader = new Uploader(this.$modal.find('.uploader'), {
                endpoint: this.endpoint,
                auto: false,
            });
            this.$uploader = $(uploader);
            this.$cropper = this.$modal.find('.image-cropper-container')

            this.$uploader.on('file-picked', $.proxy(function(ev, file, name) {
                if (HAS_FILE_API) {
                    this.crop(URL.createObjectURL(file));
                } else {
                    log.error('File APIs not supported');
                }
            }, this));

            this.$btn_clear.click(this.f('clear'));

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
            this.$uploader[0].clear();
        },

        upload: function() {
            this
        }

    });


    $('.image-picker').each(function() {
        new ImagePicker(this, $(this).siblings('.image-picker-btn'));
    });
});
