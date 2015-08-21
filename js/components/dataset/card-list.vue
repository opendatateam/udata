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
    <box title="{{ title }}" icon="cubes"
        boxclass="box-solid datasets-cards-widget"
        footerClass="text-center" footer="true">
        <div class="row" v-el="sortable">
            <div class="col-md-6 dataset-card-container"
                v-repeat="datasetid: editing ? sorted : datasets |ids"
                data-id="{{datasetid}}"
            >
                <button type="button" class="close"
                    v-if="editing"
                    v-on="click: on_remove(datasetid)">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <dataset-card datasetid="{{datasetid}}"></dataset-card>
            </div>
        </div>
        <footer>
            <a v-show="!editing" class="text-uppercase footer-btn pointer"
                v-on="click: edit">
                {{ _('Edit') }}
            </a>
            <div v-show="editing" class="input-group input-group-sm text-left">
                <span class="input-group-addon">
                    <span class="fa fa-cubes"></span>
                </span>
                <dataset-completer v-ref="completer"></dataset-completer>
                <span class="input-group-btn">
                    <button class="btn btn-success" type="button"
                        v-on="click: submit">
                        <span class="fa fa-check"></span>
                    </button>
                    <button class="btn btn-warning" type="button"
                        v-on="click: cancel">
                        <span class="fa fa-close"></span>
                    </button>
                </span>
            </div>
        </footer>
    </box>
</template>

<script>
'use strict';

var Sorter = require('mixins/sorter');

module.exports = {
    name: 'datasets-card-list',
    mixins: [Sorter],
    components: {
        'box': require('components/containers/box.vue'),
        'dataset-card': require('components/dataset/card.vue'),
        'dataset-completer': require('components/form/dataset-completer')
    },
    props: ['title', 'datasets'],
    data: function() {
        return {
            title: this._('Datasets'),
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
        on_remove: function(datasetid) {
            this.sorted.splice(this.sorted.indexOf(datasetid), 1);
            this.$dispatch('dataset-card-list:remove', datasetid);
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
                this.$.completer.selectize.focus();
            }
        }
    }
};
</script>
