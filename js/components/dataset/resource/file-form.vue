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
    :fields="fields" :model="resource" v-ref:form>
</form-horizontal>
<div v-show="!resource.url && files.length" v-for="file in files" class="info-box bg-aqua">
    <span class="info-box-icon">
        <span class="fa fa-cloud-upload"></span>
    </span>
    <div class="info-box-content">
        <span class="info-box-text">{{file.name}}</span>
        <span class="info-box-number">{{file.filesize | filesize}}</span>
        <div class="progress">
            <div class="progress-bar" :style="{width: progress+'%'}"></div>
        </div>
        <span class="progress-description">
        {{progress}}%
        </span>
    </div>
</div>
<form-horizontal v-if="resource.url"
    :fields="file_fields" :model="resource" :readonly="true">
</form-horizontal>
<div v-if="!files.length" class="resource-upload-dropzone">
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
            <span v-el:upload-btn class="btn btn-outline btn-flat">
            {{ _("Select a file from your computer") }}
            </span>
        </div>
    </div>
</div>
</template>

<script>
import API from 'api';
import Dataset from 'models/dataset';
import CommunityResource from 'models/communityresource';
import UploaderMixin from 'mixins/uploader';


export default {
    mixins: [UploaderMixin],
    props: {
        dataset: {
            type: Object,
            required: true
        },
        resource: {
            type: Object,
            default() {return new Resource()}
        },
    },
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'published',
                    label: this._('Publication date'),
                    widget: 'date-picker'
                }],
            file_fields: [{
                    id: 'url',
                    label: this._('URL'),
                    readonly: true,
                    widget: 'url-field',
                }, {
                    id: 'filesize',
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
            progress: 0,
        };
    },
    computed: {
        is_community() {
            return this.resource instanceof CommunityResource;
        },
        upload_endpoint() {
            let operations = API.datasets.operations;
            let params = {};
            let endpoint = 'upload_';
            if (typeof this.dataset !== 'undefined') {
                params = {dataset: this.dataset.id};
            }
            if (this.is_community) {
                endpoint += 'community_';
                params.community = this.resource.id;
            } else {
                endpoint += 'dataset_';
            }
            if (this.resource.id) {
                endpoint += 'resource';
                params.rid = this.resource.id;
            } else {
                endpoint += 'resources';
            }
            return operations[endpoint].urlify(params);
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
            if (!this.is_community) {
                this.dataset.resources.unshift(response);
            }
            // Do not override an existing typed or registered title.
            let title = this.$refs.form.serialize().title || this.resource.title;
            if (title) {
                response.title = title;
            }
            this.resource.on_fetched({obj: response});
        }
    },
    methods: {
        validate: function() {
            return this.$refs.form.validate();
        },
        serialize: function() {
            return this.$refs.form.serialize();
        }
    }
};
</script>
