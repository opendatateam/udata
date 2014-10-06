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
        init: function(el) {
            this.$el = $(el);

            this.$el.click(this.f('on_click'));
            this.sizes = $((this.$el.data('sizes') || '100').split(','))
                .map(parseInt)
                .filter(function(value) {
                    return !isNaN(value);
                });

            log.info('ImagePicker initialized', this.sizes);
        },

        f: function(func) {
            return $.proxy(this[func], this);
        },

        on_click: function() {
            this.$modal = modal({
                title: i18n._('Choose an image'),
                content: tpl({
                    sizes: this.sizes
                }),
                size: 'lg',
                close_btn: i18n._('Cancel'),
                close_cls: 'btn-warning',
                actions: [{
                    label: i18n._('Submit'),
                    icon: 'fa-check',
                    classes: 'btn-info btn-submit hide'
                }]
            });

            var uploader = new Uploader(this.$modal.find('.uploader'), {
                endpoint: 'upload',
                auto: false
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

            return false;
        },

        crop: function(image) {
            this.$modal.find('section').addClass('hide');
            this.$modal.find('.btn-submit').removeClass('hide');
            this.$modal.find('.modal-title').text(i18n._('Crop your thumbnail'));
            this.$cropper.removeClass('hide');

            this.cropper = new Cropper(this.$cropper, {
                size: [this.sizes]
            });

            this.cropper.load(image);
        }

    });


    $('.image-picker-btn').each(function() {
        new ImagePicker(this);
    });
});
