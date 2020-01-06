<style lang="less">
.resources-widget {
    .sort-placeholder {
        background: #C8EBFB !important;
    }

    .handle {
        cursor: move;
    }

    table.table {
        width:100%;
        table-layout:fixed;

        td.ellipsis {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        td .progress {
            margin-top: 5px;
        }
    }

    .drop-active > & {
        border: 4px dashed #bbb;
        min-height: 150px;
    }

    .box-footer > button:not(:last-child) {
        margin-right: 10px;
    }
}
</style>

<template>
<div>
    <box :title="title" icon="file"
        boxclass="box-solid resources-widget"
        bodyclass="table-responsive no-padding"
        footerclass="text-center"
        :footer="$root.me.can_edit(dataset)" :empty="_('No resources')">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th v-if="reordering" width="30"></th>
                    <th v-i18n="Name"></th>
                    <th width="100" v-i18n="Type"></th>
                    <th width="100" v-i18n="Format"></th>
                    <th width="100" v-i18n="Size"></th>
                    <th width="120" v-i18n="Downloads"></th>
                    <th width="100" v-i18n="Availability"></th>
                </tr>
            </thead>
            <tbody v-el:sortable>
                <tr v-for="file in files" track-by="id">
                    <td v-if="reordering"></td>
                    <td>
                        <div class="ellipsis">{{ file.name }}</div>
                    </td>
                    <td><!-- resource.type --></td>
                    <td>{{ file.name | fileext }}</td>
                    <td>{{ file.size | filesize }}</td>
                    <td colspan="2">
                        <div class="progress progress-xs progress-striped active">
                            <div class="progress-bar progress-bar-primary"
                                id="progress-{{file.id}}" style="width: 0%"></div>
                        </div>
                    </td>
                </tr>
                <tr v-for="resource in dataset.resources" @click="display(resource)"
                    :class="{ 'pointer': !reodering, 'move': reordering }"
                    :data-id="resource.id">
                    <td v-if="reordering" class="handle">
                        <span class="fa fa-bars"></span>
                    </td>
                    <td class="ellipsis">{{ resource.title }}</td>
                    <td>{{ resource | resource_type_label }}</td>
                    <td>{{ resource.format }}</td>
                    <td>{{ resource.filesize | filesize }}</td>
                    <td class="text-center">
                        <span class="badge" :class="{
                            'bg-green': resource.metrics.views > 0,
                            'bg-red': (resource.metrics.views || 0) === 0
                            }">
                            {{ resource.metrics.views || 0 }}
                        </span>
                    </td>
                    <td class="text-center">
                        <resource-availability :resource="resource"></resource-availability>
                    </td>
                </tr>
                <tr v-if="!(dataset && dataset.resources)" class="text-center lead">
                    <td colspan="3" v-i18n="No resources"></td>
                </tr>
            </tbody>
        </table>
        <div class="overlay dropzone" v-if="dropping">
            <span class="fa fa-download fa-2x"></span>
        </div>
        <footer slot="footer" v-if="$root.me.can_edit(dataset)">
            <button type="button"
                class="btn btn-primary btn-sm btn-flat pointer"
                v-show="!reordering"
                @click="on_new">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="Add"></span>
            </button>
            <button type="button"
                class="btn btn-primary btn-sm btn-flat pointer"
                v-show="!reordering && dataset.resources && dataset.resources.length > 1"
                @click="reorder">
                <span class="fa fa-fw fa-sort"></span>
                <span v-i18n="Reorder"></span>
            </button>
            <button type="button" class="btn btn-success btn-sm btn-flat pointer"
                v-show="reordering"
                @click="reorder_done(true)">
                <span class="fa fa-fw fa-check"></span>
                <span v-i18n="Apply"></span>
            </button>
            <button type="button" class="btn btn-warning btn-sm btn-flat pointer"
                v-show="reordering"
                @click="reorder_done(false)">
                <span class="fa fa-fw fa-times"></span>
                <span v-i18n="Cancel"></span>
            </button>
        </footer>
    </box>
</div>
</template>

<script>
import Vue from 'vue';
import API from 'api';
import Sorter from 'mixins/sorter';
import Uploader from 'mixins/uploader';
import Box from 'components/containers/box.vue';
import ResourceAvailability from './availability.vue';
import DatasetFilters from 'components/dataset/filters';

export default {
    name: 'resources-list',
    mixins: [Uploader, Sorter, DatasetFilters],
    components: {Box, ResourceAvailability},
    props: {
        dataset: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            reordering: false,
            new_order: []
        };
    },
    computed: {
        title() {
            return this.dropping ? Vue._('Drop resource') : Vue._('Resources');
        }
    },
    events: {
        'uploader:progress': function(id, uploaded, total) {
            const el = document.getElementById(`progress-${id}`);
            el.style.width = `${Math.round(uploaded * 100 / total)}%`;
        },
        'uploader:complete': function(id, response, file) {
            this.files.$remove(file);
            this.dataset.resources.unshift(response);
        },
        'uploader:error': function(id) {
            // Remove the progressing file (an error is already displayed globally)
            const file = this.$uploader.getFile(id);
            this.files.splice(this.files.indexOf(file), 1);
        }
    },
    ready() {
        /* In case of a new resource, we display the appropriated popin
           on load. */
        if ("new_resource" in this.$route.query) {
            this.on_new();
        }
    },
    methods: {
        on_new() {
            this.$root.$modal(
                require('components/dataset/resource/add-modal.vue'),
                {dataset: this.dataset}
            );
        },
        reorder() {
            this.$sortable.option('disabled', false);
            this.$dnd.dispose();
            this.reordering = true;
            this._initial_order = this.$sortable.toArray();
        },
        reorder_done(toReorder) {
            this.$sortable.option('disabled', true);
            this.reordering = false;
            this.$dnd.setupExtraDropzone(this.$el);
            if (toReorder) {
                this.dataset.reorder(this.$sortable.toArray());
            } else {
                this.$sortable.sort(this._initial_order);
            }
        },
        display(resource) {
            if (!this.reordering) {
                this.$go({name: 'dataset-resource', params: {
                    oid: this.dataset.id, rid: resource.id
                }});
            }
        }
    },
    sortable: {
        disabled: true,
        draggable: 'tr',
        ghostClass: 'sort-placeholder',
    },
    watch: {
        'dataset.id': function(id) {
            if (id) {
                this.upload_endpoint = API.datasets.operations.upload_new_dataset_resource.urlify({dataset: id});
            }
        }
    }
};
</script>
