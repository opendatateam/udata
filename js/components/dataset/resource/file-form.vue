<style lang="less">
.resource-upload-dropzone {
    border: 4px dashed #bbb;
    min-height: 150px;
    padding-top: 10px;
    padding-bottom: 10px;

    .lead {
        margin-bottom: 0;
    }
}
</style>

<template>
<form-horizontal class="resource-form file-resource-form"
    fields="{{fields}}" model="{{resource}}" v-ref="form">
</form-horizontal>
<div v-if="!resource.url && !files.length" class="resource-upload-dropzone">
    <div class="row">
        <div class="text-center col-xs-12">
            <span class="fa fa-download fa-4x dropicon"></span>
        </div>
        <div class="text-center col-xs-12 lead">
            <p>{{ _("Drag a file here") }}</p>
        </div>
        <div class="text-center col-xs-12">
            <p>{{ _( "or") }}</p>
        </div>
        <div class="text-center col-xs-12">
            <button v-el="uploadBtn" type="button" class="btn btn-outline btn-flat">
            {{ _("Select a file from your computer") }}
            </button>
        </div>
    </div>
</div>
<div v-show="!resource.url && files.length" v-repeat="file:files" class="info-box bg-aqua">
    <span class="info-box-icon">
        <span class="fa fa-cloud-upload"></span>
    </span>
    <div class="info-box-content">
        <span class="info-box-text">{{file.name}}</span>
        <span class="info-box-number">{{file.size | filesize}}</span>
        <div class="progress">
            <div class="progress-bar" style="width: {{progress}}%"></div>
        </div>
        <span class="progress-description">
        {{progress}}%
        </span>
    </div>
</div>
<form-horizontal v-if="resource.url"
    fields="{{file_fields}}" model="{{resource}}" readonly="true">
</form-horizontal>
</template>

<script>
'use strict';

var API = require('api'),
    $ = require('jquery'),
    endpoint = API.datasets.operations.upload_resource;

module.exports = {
    inherit: true,
    mixins: [require('mixins/uploader')],
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }],
            file_fields: [{
                    id: 'url',
                    label: this._('URL'),
                    readonly: true
                }, {
                    id: 'size',
                    label: this._('Size'),
                    readonly: true
                }, {
                    id: 'format',
                    label: this._('Format'),
                    widget: 'format-completer',
                    readonly: true
                }, {
                    id: 'mime',
                    label: this._('Mime Type'),
                    readonly: true
                }, {
                    id: 'checksum',
                    label: this._('Checksum'),
                    widget: 'checksum',
                    readonly: true
                }],
            upload_multiple: false,
            progress: 0
        };
    },
    computed: {
        upload_endpoint: function() {
            return endpoint.urlify({dataset: this.dataset.id});
        }
    },
    components: {
        'form-horizontal': require('components/form/horizontal-form.vue')
    },
    events: {
        'uploader:progress': function(id, uploaded, total) {
            this.progress = Math.round(uploaded * 100 / total);
        },
        'uploader:complete': function(id, response) {
            // var file = this.$uploader.getFile(id);
            // this.files.$remove(this.files.indexOf(file));
            this.dataset.resources.unshift(response);
            this.resource.on_fetched({obj: response});
        }
    },
    methods: {
        validate: function() {
            return this.$.form.validate();
        },
        serialize: function() {
            return $.extend(this.resource.$data, this.$.form.serialize());
            // var data = this.$.form.serialize();
        }
    }
};
</script>
