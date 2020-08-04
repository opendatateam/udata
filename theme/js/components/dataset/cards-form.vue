<style lang="less">
@card-padding: 8px;

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
        margin-bottom: 10px;

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
// }
</style>

<template>
<div>
    <div class="row completer-row">
        <div class="col-lg-10 col-lg-offset-1">
            <div class="input-group">
                <span class="input-group-addon">
                    <span class="fa fa-cubes"></span>
                </span>
                <completer v-ref:completer></completer>
            </div>
        </div>
    </div>
    <div class="row" v-show="!datasets.length">
        <p class="lead text-center">{{ _('No related datasets') }}</p>
    </div>
    <div class="card-list card-list--columned" v-el:sortable v-show="datasets.length">
        <div class="col-xs-12 col-md-6 col-lg-4 dataset-card-container"
            v-for="datasetid in datasets | ids"
            :data-id="datasetid">
            <button type="button" class="close" @click="on_remove(datasetid)">
                <span aria-hidden="true">&times;</span>
                <span class="sr-only" v-i18n="Remove"></span>
            </button>
            <card :datasetid="datasetid"></card>
        </div>
    </div>
</div>
</template>

<script>
import Sorter from 'mixins/sorter';
import Card from 'components/dataset/card.vue';
import Completer from 'components/form/dataset-completer.vue';

export default {
    name: 'datasets-cards-form',
    mixins: [Sorter],
    components: {Card, Completer},
    props: {
        datasets: {
            type: Array,
            default() {
                /* Prefill the datasets with optional ids contained in
                   `dataset_id` GET parameter. */
                let datasets = [];
                if ("dataset_id" in this.$route.query) {
                    // There might be a single id or a list.
                    const datasetIds = this.$route.query.dataset_id;
                    if (typeof datasetIds === "string") {
                        datasets.push(datasetIds);
                    } else {
                        datasets = datasets.concat(datasetIds);
                    }
                }
                return datasets;
            }
        }
    },
    events: {
        'completer:item-add': function(dataset_id, $item) {
            $item.remove();
            this.datasets.push(dataset_id);
            this.$dispatch('dataset-card-list:add', dataset_id);
            return true;
        }
    },
    methods: {
        on_remove(dataset_id) {
            this.datasets.splice(this.datasets.indexOf(dataset_id), 1);
            this.$dispatch('dataset-card-list:remove', dataset_id);
        }
    },
    sortable: {
        draggable: '.dataset-card-container',
        ghostClass: 'ghost',
    }
};
</script>
