<style lang="less">
.datasets-cards-widget {
    @field-height: 34px;
    @card-padding: 8px;

    .box-footer {
        padding: 0;
        .search {
            height: @field-height;
        }

        .footer-btn {
            display: block;
            height: @field-height;
            line-height: @field-height;
        }
    }

    .selectize-control {
        height: @field-height;
    }

    .selectize-dropdown {
        position: absolute;
    }

    .input-group-btn .btn {
        border: none;
        height: @field-height;
        border-radius: 0;
    }

    .dataset-card-container {
        button.close {
            position: absolute;
            right: @card-padding + 12px;
            top: 5px;
            z-index: 15;
            color: red;
            opacity: 1;

            &:hover {
                right: @card-padding + 10px;
                top: 2px;
                font-size: 2em;
            }
        }

        &.ghost {
            opacity: 0.5;

            button.close {
                display: none;
            }

            .dataset-card {
                border: 2px dashed gray;
            }
        }
    }
}
</style>

<template>
<div>
    <box :title="title" icon="cubes"
        boxclass="box-solid datasets-cards-widget"
        footerclass="text-center" :footer="true" :loading="loading">
        <div class="card-list card-list--columned" v-el:sortable>
            <div class="col-xs-12 dataset-card-container"
                v-for="dataset in (editing ? sorted : datasets)"
                :data-id="dataset.id"
            >
                <button type="button" class="close"
                    v-if="editing"
                    @click="on_remove(dataset)">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <dataset-card :dataset="dataset"></dataset-card>
            </div>
        </div>
        <footer v-if="editable" slot="footer">
            <a v-show="!editing" class="text-uppercase footer-btn pointer"
                @click="edit">
                {{ _('Edit') }}
            </a>
            <div v-show="editing" class="input-group input-group-sm text-left">
                <span class="input-group-addon">
                    <span class="fa fa-cubes"></span>
                </span>
                <dataset-completer v-ref:completer></dataset-completer>
                <span class="input-group-btn">
                    <button class="btn btn-success" type="button"
                        @click="submit">
                        <span class="fa fa-check"></span>
                    </button>
                    <button class="btn btn-warning" type="button"
                        @click="cancel">
                        <span class="fa fa-close"></span>
                    </button>
                </span>
            </div>
        </footer>
    </box>
</div>
</template>

<script>
import Sorter from 'mixins/sorter';
import Dataset from 'models/dataset';
import DatasetCard from 'components/dataset/card.vue';
import Box from 'components/containers/box.vue';
import DatasetCompleter from 'components/form/dataset-completer.vue';

export default {
    name: 'dataset-card-list',
    mixins: [Sorter],
    MASK: DatasetCard.MASK,
    components: {Box, DatasetCompleter, DatasetCard},
    props: {
        title: {
            type: String,
            default() {return this._('Datasets')}
        },
        datasets: Array,
        editable: Boolean,
        loading: Boolean
    },
    data() {
        return {
            editing: false,
            sorted: []
        };
    },
    events: {
        'completer:item-add': function(dataset_id, $item) {
            $item.remove();
            this.sorted.push(new Dataset({mask: this.$options.MASK}).fetch(dataset_id));
            this.$dispatch('dataset-card-list:add', dataset_id);
        },
        'sorter:update': function(evt) {
            // Order from sortable
            this.sorted = this.$sortable.toArray().map(id => this.sorted.find(dataset => dataset.id === id));
        },
    },
    methods: {
        edit() {
            this.$sortable.option('disabled', false);
            this.sorted = this.datasets.slice(0);
            this.editing = true;
        },
        submit() {
            this.$dispatch('dataset-card-list:submit', this.$sortable.toArray());
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
        },
        cancel() {
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
        },
        on_remove(dataset) {
            this.sorted.splice(this.sorted.indexOf(dataset), 1);
            this.$dispatch('dataset-card-list:remove', dataset.id);
        }
    },
    sortable: {
        disabled: true,
        draggable: '.dataset-card-container',
        ghostClass: 'ghost',
    },
    watch: {
        editing(editing) {
            if (editing) {
                this.$refs.completer.selectize.focus();
            }
        }
    }
};
</script>
