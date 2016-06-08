<!--
    Image picker
-->
<style lang="less">
.image-picker {

    .uploader {
        .drop-pane {
            padding: 15px;
            margin: 15px 0;
            border: 5px dashed lighten(black, 60%);

            &.drop-active {
                border-color: blue;
            }
        }
    }
}
</style>

<template>
<div class="image-picker">
    <div class="uploader" v-if="!resizing && !files.length">
        <div class="row drop-pane">
            <div class="text-center col-xs-12">
                <span class="fa fa-download fa-4x dropicon"></span>
            </div>
            <div class="text-center col-xs-12 lead">
                <p>{{ _('Drag a picture here') }}</p>
            </div>
            <div class="text-center col-xs-12">
                <p>{{ _('or') }}</p>
            </div>
            <div class="text-center col-xs-12">
                <span class="btn btn-outline btn-flat" v-el:upload-btn>
                    {{ _('Select a file from your computer') }}
                </span>
            </div>
        </div>
    </div>
    <div v-if="!resizing && files.length" class="info-box bg-aqua">
        <span class="info-box-icon">
            <span class="fa fa-cloud-upload"></span>
        </span>
        <div class="info-box-content">
            <span class="info-box-text">{{file.name}}</span>
            <span class="info-box-number">{{file.size | filesize}}</span>
            <div class="progress">
                <div class="progress-bar" :style="{width: progress+'%'}"></div>
            </div>
            <span class="progress-description">
            {{progress}}%
            </span>
        </div>
    </div>
    <div class="row progress-pane hide" v-if="files.length">
        <div class="col-xs-12">
            <div class="progress">
                <div class="progress">
                    <div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    </div>
                </div>
            </div>
        </div>
    </div>
    <thumbnailer v-ref:thumbnailer v-if="resizing" :src="src" :sizes="sizes">
    </thumbnailer>
</div>
</template>

<script>
import $ from 'jquery';
import API from 'api';
import log from 'logger';
import UploaderMixin from 'mixins/uploader';

export default {
    autoUpload: false,
    mixins: [UploaderMixin],
    data: function() {
        return {
            src: null,
            resizing: false,
        };
    },
    props: {
        endpoint: null,
        sizes: {
            type: Array,
            default: function() {return [100];}
        }
    },
    components: {
        thumbnailer: require('components/widgets/thumbnailer.vue')
    },
    computed: {
        file: function() {
            if (this.files.length > 0) {
                return this.files[0];
            }
        },
        upload_endpoint: function() {
            return this.endpoint;
        }
    },
    events: {
        'uploader:file-submit': function(id, file) {
            if (this.HAS_FILE_API) {
                this.src = URL.createObjectURL(file);
                this.resizing = true;
            } else {
                log.warning('File APIs not supported');
                this.upload();
            }
            return true;
        },
        'uploader:progress': function(id, uploaded, total) {
            this.progress = Math.round(uploaded * 100 / total);
            return true;
        },
        'uploader:complete': function(id, response) {
            if (this.HAS_FILE_API) {
                this.$dispatch('image:saved');
            } else {
                this.src = response.url;
                this.resizing = true;
            }
            return true;
        }
    },
    methods: {
        save: function() {
            if (this.HAS_FILE_API) {
                let data = {};
                if (this.$refs.thumbnailer.bbox) {
                    data.bbox = this.$refs.thumbnailer.bbox;
                }
                this.upload(data);
            } else {
                this.$dispatch('image:saved');
            }
        }
    }
};
</script>
