define([
    'jquery',
    'class',
    'logger',
    'i18n',
    'templates/widgets/cropper.hbs',
    'jquery-jcrop'
], function($, Class, log, i18n, tpl) {
    'use strict';

    var DEFAULTS = {
        sizes: [100],
    };

    var Cropper = Class.extend({
        init: function(el, options) {
            this.$el = $(el);
            this.options = $.extend({}, DEFAULTS, options);

            // Render
            this.$el.html(tpl({
                sizes: this.options.sizes
            }));

            this.$crop_pane = this.$el.find('.crop-pane');
            this.$cropper = this.$crop_pane.find('.cropper');

            this.$preview_pane = this.$el.find('.preview-pane');
            this.$preview = this.$preview_pane.find('.preview');
            this.$preview_containers = this.$preview_pane.find('.preview-container');
            this.$checkbox = this.$preview_pane.find('input[type=checkbox]');

            this.$checkbox.change(this.f('toggle_center'));

            log.debug('Cropper initialized');
        },

        f: function(func) {
            return $.proxy(this[func], this);
        },

        load: function(src) {
            var that = this,
                max_width = this.$crop_pane.width(),
                max_height = parseInt(this.$crop_pane.css('max-height').replace('px', ''));

            this.$preview.attr('src', src);
            this.$cropper
                .attr('src', src)
                .Jcrop({
                    onChange: this.f('preview'),
                    onSelect: this.f('preview'),
                    aspectRatio: 1,
                    boxWidth: max_width,
                    boxHeight: max_height
                }, function() {
                    var bounds = this.getBounds(),
                        size = Math.min(bounds[0], bounds[1]);

                    that.Jcrop = this;
                    this.setSelect([0, 0, size, size]);
                });
        },

        /**
         * Toggle centering
         */
        toggle_center: function() {
            var enabled = this.$checkbox.is(':checked');
            if (enabled) {
                var bounds = this.Jcrop.getBounds(),
                    attr = bounds[0] > bounds[1] ? 'width' : 'height';

                this.Jcrop.disable();
                this.$crop_pane.addClass('centered');
                this.$preview_containers.addClass('centered');
                this.$preview.removeAttr('style').css(attr, '100%');
            } else {
                this.Jcrop.enable();
                this.$crop_pane.removeClass('centered');
                this.$preview_containers.removeClass('centered');
            }
        },

        /**
         * Adjust the preview given the cropper position and size
         */
        preview: function(coords) {
            var bounds = this.Jcrop.getBounds(),
                w = bounds[0],
                h = bounds[1];

            this.$preview_containers.each(function() {
                var $this = $(this),
                    px = $this.width(),
                    py = $this.height(),
                    rx = px / coords.w,
                    ry = py / coords.h;

                $this.find('.preview').removeAttr('style').css({
                    width: Math.round(rx * w) + 'px',
                    height: Math.round(ry * h) + 'px',
                    marginLeft: '-' + Math.round(rx * coords.x) + 'px',
                    marginTop: '-' + Math.round(ry * coords.y) + 'px'
                });
            });
        },

        /**
         * Get the current selected crop Bounding Box (realsize) if any.
         */
        get_bbox: function() {
            if (!this.$checkbox.is(':checked')) {
                var selection = this.Jcrop.tellSelect();
                return [selection.x, selection.y, selection.x2, selection.y2];
            }
        }

    });


    return Cropper;
});
