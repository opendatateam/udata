define([
    'jquery',
    'class',
    'logger',
    'i18n',
    'hbs!templates/widgets/cropper',
    'jcrop'
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
            this.$cropper = this.$crop_pane.find('.cropper'),

            this.$preview_pane = this.$el.find('.preview-pane');
            this.$preview = this.$preview_pane.find('.preview'),
            this.$preview_containers = this.$preview_pane.find('.preview-container'),

            log.debug('Cropper initialized');
        },

        f: function(func) {
            return $.proxy(this[func], this);
        },

        load: function(src) {
            var that = this,
                max_width , max_height;


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

                $this.find('.preview').css({
                    width: Math.round(rx * w) + 'px',
                    height: Math.round(ry * h) + 'px',
                    marginLeft: '-' + Math.round(rx * coords.x) + 'px',
                    marginTop: '-' + Math.round(ry * coords.y) + 'px'
                });
            });
        }

    });


    return Cropper;
});
