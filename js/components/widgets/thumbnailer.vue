<!--
    Thumbnailer widget
-->
<style lang="less">
.thumbnailer {
    img {
        max-width: none !important;
    }

    .crop-pane {
        min-height: 200px;
        max-height: 600px;

        .jcrop-holder {
            margin: auto;

            border: 1px solid black;

            -webkit-box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);
               -moz-box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);
                    box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);

            .centered& {
                :not(.cropper) {
                    display: none;
                }

                .cropper {
                    opacity: 1 !important;
                }
            }
        }
    }

    .preview-pane {

        /* The Javascript code will set the aspect ratio of the crop
           area based on the size of the thumbnail preview,
           specified here */
        .preview-container {
            overflow: hidden;
            border: 1px solid black;
            margin-bottom: 15px;

            -webkit-box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);
               -moz-box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);
                    box-shadow: 1px 1px 5px 2px rgba(0, 0, 0, 0.2);

            .centered& {
                // vertical-align: middle;
                text-align: center;

                > img {
                    &:before { /* create a full-height inline block pseudo=element */
                        content: ' ';
                        display: inline-block;
                        vertical-align: middle;
                        height: 100%;
                    }

                    vertical-align: middle;
                    display: inline-block;
                    max-width: 100%;
                    max-height: 100%;
                }
            }
        }
    }
}
</style>

<template>
<div class="thumbnailer" v-if="preview" v-class="centered: centered">
    <div class="row">
        <div class="col-xs-12 col-sm-8 crop-pane" v-el="crop_pane">
            <img class="cropper" v-el="cropper"/>
        </div>
        <div class="col-xs-12 col-sm-4 preview-pane" v-el="preview_pane">
            <div class="checkbox">
                <label>
                    <input type="checkbox" v-el="checkbox" v-model="centered">
                    {{ _('Center the full picture') }}
                </label>
            </div>
            <h5>{{ _('Preview') }}</h5>
            <div class="preview-container" v-repeat="size: sizes"
                v-el="preview_containers"
                style="width: {{size}}px; height: {{size}}px;">
                <img class="preview" alt="{{ _('Preview') }}" v-el="previews" v-attr="src: src"/>
            </div>
        </div>
    </div>
</div>
</template>

<script>
'use strict';

var JCrop = require('jquery-jcrop'),
    $ = require('jquery');

module.exports = {
    mixins: [require('mixins/uploader')],
    props: ['src', 'sizes'],
    data: function() {
        return {
            centered: false,
            sizes: [50, 100],
            src: null
        };
    },

    computed: {
        /**
         * Get the current crop Bounding Box (realsize) if any.
         */
        bbox: function() {
            if (!this.$$.checkbox.checked) {
                var selection = this.Jcrop.tellSelect();
                return [selection.x, selection.y, selection.x2, selection.y2];
            }
        }
    },
    methods: {
        /**
         * Adjust the preview given the cropper position and size
         */
        preview: function(coords) {
            var bounds = this.Jcrop.getBounds(),
                w = bounds[0],
                h = bounds[1];

            this.$$.preview_containers.forEach(function(el) {
                var $el = $(el),
                    px = $el.width(),
                    py = $el.height(),
                    rx = px / coords.w,
                    ry = py / coords.h;

                $el.find('.preview').removeAttr('style').css({
                    width: Math.round(rx * w) + 'px',
                    height: Math.round(ry * h) + 'px',
                    marginLeft: '-' + Math.round(rx * coords.x) + 'px',
                    marginTop: '-' + Math.round(ry * coords.y) + 'px'
                });
            });
        },
        setImage: function(src) {
            if (!src) return;

            var that = this,
                $pane = $(this.$$.crop_pane),
                max_width = $pane.width(),
                max_height = parseInt($pane.css('max-height').replace('px', ''));

            $(this.$$.cropper)
                .attr('src', src)
                .Jcrop({
                    onChange: this.preview.bind(this),
                    onSelect: this.preview.bind(this),
                    aspectRatio: 1,
                    boxWidth: max_width,
                    boxHeight: max_height
                }, function() {
                    var bounds = this.getBounds(),
                        size = Math.min(bounds[0], bounds[1]);

                    that.Jcrop = this;
                    this.setSelect([0, 0, size, size]);
                });
        }
    },
    watch: {
        /**
         * Toggle centering
         */
        centered: function(centered) {
            if (centered) {
                var bounds = this.Jcrop.getBounds(),
                    attr = bounds[0] > bounds[1] ? 'width' : 'height';

                this.Jcrop.disable();

                $(this.$$.preview_containers)
                    .find('.preview')
                    .removeAttr('style')
                    .css(attr, '100%');
            } else {
                this.Jcrop.enable();
            }
        },
        src: function(src) {
            return this.setImage(src);
        }
    },
    ready: function() {
        this.setImage(this.src);
    }
};
</script>
