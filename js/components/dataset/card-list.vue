<style lang="less">
.datasets-cards-widget {
    @field-height: 34px;

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
            position: relative;
            right: 10px;
            top: 5px;
            z-index: 15;
            color: red;
            opacity: 1;

            &:hover {
                right: 8px;
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
    <box :title="title" icon="cubes"
        boxclass="box-solid datasets-cards-widget"
        footerclass="text-center" :footer="true" :loading="loading">
        <div class="row" v-el:sortable>
            <div class="col-md-6 dataset-card-container"
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
        <footer slot="footer">
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
</template>

<script>
import Sorter from 'mixins/sorter';
import DatasetCard from 'components/dataset/card.vue';
import Box from 'components/containers/box.vue';
import DatasetCompleter from 'components/form/dataset-completer.vue';

export default {
    name: 'datasets-card-list',
    mixins: [Sorter],
    MASK: DatasetCard.MASK,
    components: {Box, DatasetCompleter, DatasetCard},
    props: {
        title: {
            type: String,
            default: function() {return this._('Datasets');}
        },
        datasets: Array,
        loading: Boolean
    },
    data: function() {
        return {
            editing: false,
            sorted: []
        };
    },
    events: {
        'completer:item-add': function(dataset_id, $item) {
            $item.remove();
            this.sorted.push(dataset_id);
            this.$dispatch('dataset-card-list:add', dataset_id);
        }
    },
    methods: {
        edit: function() {
            this.$sortable.option('disabled', false);
            this._initial_order = this.$sortable.toArray();
            this.sorted = this.datasets.map(function(dataset) {
                return dataset.id;
            });
            this.editing = true;
        },
        submit: function() {
            this.$dispatch('dataset-card-list:submit', this.$sortable.toArray());
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
        },
        cancel: function() {
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
            this.$sortable.sort(this._initial_order);
        },
        on_remove: function(dataset) {
            this.sorted.splice(this.sorted.indexOf(dataset.id), 1);
            this.$dispatch('dataset-card-list:remove', dataset.id);
        }
    },
    sortable: {
        disabled: true,
        draggable: '.dataset-card-container',
        ghostClass: 'ghost',
    },
    watch: {
        editing: function(editing) {
            if (editing) {
                this.$refs.completer.selectize.focus();
            }
        }
    }
};
</script>
