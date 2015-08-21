<style lang="less">
.completer-row {
    @field-height: 34px;
    margin-bottom: 10px;

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
}
// .datasets-cards-form {


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
// }
</style>

<template>
    <div class="row">
        <div class="input-group col-lg-10 col-lg-offset-1 completer-row">
            <span class="input-group-addon">
                <span class="fa fa-cubes"></span>
            </span>
            <dataset-completer v-ref="completer"></dataset-completer>
        </div>
    </div>
    <div class="row" v-show="!datasets.length">
        <p class="lead text-center">{{ _('No related datasets') }}</p>
    </div>
    <div class="row" v-el="sortable" v-show="datasets.length">
        <div class="col-md-6 dataset-card-container"
            v-repeat="datasetid : datasets | ids"
            data-id="{{datasetid}}"
        >
            <button type="button" class="close" v-on="click: on_remove(datasetid)">
                <span aria-hidden="true">&times;</span>
                <span class="sr-only" v-i18n="Remove"></span>
            </button>
            <dataset-card datasetid="{{datasetid}}"></dataset-card>
        </div>
    </div>
</template>

<script>
'use strict';

var Sorter = require('mixins/sorter');

module.exports = {
    name: 'datasets-cards-form',
    mixins: [Sorter],
    components: {
        'dataset-card': require('components/dataset/card.vue'),
        'dataset-completer': require('components/form/dataset-completer')
    },
    props: ['datasets'],
    data: function() {
        /* Prefill the datasets with optional ids contained in
           `dataset_id` GET parameter. */
        let datasets = [];
        if ("dataset_id" in this.$router.parameters) {
            // There might be a single id or a list.
            let datasetIds = this.$router.parameters.dataset_id;
            if (typeof datasetIds === "string") {
                datasets.push(datasetIds);
            } else {
                datasets = datasets.concat(datasetIds);
            }
        }
        return {
            datasets: datasets
        };
    },
    events: {
        'completer:item-add': function(dataset_id, $item) {
            $item.remove();
            this.datasets.push(dataset_id);
            this.$dispatch('dataset-card-list:add', dataset_id);
        }
    },
    methods: {
        on_remove: function(dataset_id) {
            this.datasets.splice(this.datasets.indexOf(dataset_id), 1);
            this.$dispatch('dataset-card-list:remove', dataset_id);
        }
    },
    sortable: {
        // disabled: true,
        draggable: '.dataset-card-container',
        ghostClass: 'ghost',
    }
};
</script>
