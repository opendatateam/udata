<style lang="less">
// Mostly a duplicate from 'less/udata/publish-actions-modal.less'
// but kept as both components are meant to be separated in the
// soon to happen core/admin split
@import '~less/admin/variables';

.actions-list {
    margin-bottom: 0;

    .list-group-item {
        @base-color: #eaeaea;
        @base-size: 60px;
        @border-size: 4px;
        height: @base-size + 2 * @border-size;
        background-color: lighten(@gray-lighter, 5%);
        margin: 0px 0px 10px;
        border-radius: 0px;
        border: @border-size solid transparent;
        padding: 0;

        &:last-child {
            margin-bottom: 0;
        }

        .action-icon {
            float: left;
            width: @base-size;
            height: @base-size;
            background-color: @blue;
            margin: 0px;

            span {
                color: lighten(@gray-lighter, 10%);
                line-height: 60px;
                text-align: center;
                display: block;
            }
        }

        .list-group-item-text {
            margin-left: @base-size + 10px;
            font-weight: normal;
        }

        .list-group-item-heading {
            margin-left: @base-size + 10px;
            margin-top: 9px;
            margin-bottom: 3px;
            font-weight: bold;
        }

        &:hover {
            background-color: @gray-lighter;

            .action-icon {
                background-color: lighten(@gray-lighter, 5%);
            }
        }
    }
}

.resource-upload-dropzone {
    border: 4px dashed @gray-lte;
    min-height: 150px;
    padding-top: 10px;
    padding-bottom: 10px;
    margin-bottom: 15px;

    .lead {
        margin-bottom: 0;
    }

    .drop-active  & {
        border: 4px dashed @green;
    }

    // url field
    .col-sm-9 > div {
        margin-right: 15px;
    }
}

.resource-choose-upload {
    text-align: center;
    a {
        text-decoration: underline;
    }
}

.modal-body {
    .resource-choose-upload {
        a {
            color: white;
        }
    }
}

</style>

<template>
<div>
    <form-horizontal v-if="hasData && !isUpload" class="resource-form file-resource-form"
        :fields="fields" :model="resource" v-ref:form>
    </form-horizontal>
    <div v-for="file in files" track-by="id" class="info-box bg-aqua">
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
    <div class="resource-choose-upload" v-show="isUpload && !files.length">
        <div class="resource-upload-dropzone">
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
        <div v-if="!hasUploadedFile">
            <a href @click.prevent.stop="manual">
                {{ _("You can also link to an existing remote file or URL by clicking here.") }}
            </a>
        </div>
    </div>
</div>
</template>

<script>
import API from 'api';
import Dataset from 'models/dataset';
import Resource from 'models/resource';
import CommunityResource from 'models/communityresource';
import FormHorizontal from 'components/form/horizontal-form.vue';
import UploaderMixin from 'mixins/uploader';
import resource_types from 'models/resource_types';

export default {
    components: {FormHorizontal},
    mixins: [UploaderMixin],
    props: {
        dataset: {
            type: Object,
            default() {return new Dataset()}
        },
        resource: {
            type: Object,
            default() {
                return new Resource({
                    data: {
                        filetype: 'remote',
                        type: 'main',
                    }
                }
            )}
        },
        isUpload: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            hasChosenRemoteFile: false,
            generic_fields: [{
                    id: 'title',
                    label: this._('Title')
                },{
                    id: 'type',
                    label: this._('Type'),
                    widget: 'select-input',
                    values: resource_types,
                    map: function(item) {
                        return {value: item.id, text: item.label};
                    }
                }, {
                    id: 'description',
                    label: this._('Description'),
                    rows:3,
                }, {
                    id: 'published',
                    label: this._('Publication date'),
                    widget: 'date-picker'
                }],
            progress: 0,
        };
    },
    computed: {
        canDrop() {
            return this.isUpload && !this.files.length;
        },
        hasData() {
            return Boolean(this.resource.url || this.hasChosenRemoteFile);
        },
        hasUploadedFile() {
            return this.resource.filetype == 'file';
        },
        file_fields() {
            const readonly = this.resource.filetype === 'file';
            return [{
                id: 'url',
                label: this._('URL'),
                widget: 'url-field',
                readonly,
            }, {
                id: 'filesize',
                label: this._('Size'),
                readonly,
            }, {
                id: 'format',
                label: this._('Format'),
                widget: 'format-completer',
                readonly,
            }, {
                id: 'mime',
                label: this._('Mime Type'),
                readonly,
            }, {
                id: 'checksum',
                label: this._('Checksum'),
                widget: 'checksum',
                readonly,
            }]
        },
        fields() {
            return this.generic_fields.concat(this.file_fields);
        },
        is_community() {
            return this.resource instanceof CommunityResource;
        },
        upload_endpoint() {
            const operations = API.datasets.operations;
            let params = {};
            if (typeof this.dataset !== 'undefined') {
                params = {dataset: this.dataset.id};
            }
            if (this.resource.id) {
                if (this.is_community) {
                    params.community = this.resource.id;
                } else {
                    params.rid = this.resource.id;
                }
            }
            const route_new = this.resource.id ? '' : 'new_';
            const route_namespace = this.is_community ? 'community_' : 'dataset_';
            const endpoint = `upload_${route_new}${route_namespace}resource`;
            return operations[endpoint].urlify(params);
        },
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
            if (this.$refs.form) {
                const title = this.$refs.form.serialize().title || this.resource.title;
                if (title) {
                    response.title = title;
                }
            }
            this.resource.on_fetched({obj: response});
            this.postUpload();
        },
    },
    methods: {
        manual() {
            this.hasChosenRemoteFile = true;
            this.resource.filetype = 'remote';
            this.isUpload = false;
        },
        postUpload() {
            this.resource.filetype = 'file';
            this.isUpload = false;
        },
        serialize() {
            // Required because of readonly fields and filetype.
            return Object.assign({}, this.resource, this.$refs.form.serialize());
        },
        validate() {
            return this.$refs.form.validate();
        },
        on_error(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
