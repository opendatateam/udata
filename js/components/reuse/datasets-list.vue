<template>
    <box-container title="{{ title }}" icon="cubes"
        boxclass="box-solid reused-datasets-widget"
        footerClass="text-center">
        <div class="row">
            <dataset-card class="col-md-6"
                v-repeat="datasetid: reuse.datasets | ids"
            ></dataset-card>

        </div>
        <box-footer>
            <a class="uppercase">{{ _('Add') }}</a>
        </box-footer>
    </box-container>
</template>

<script>
'use strict';

module.exports = {
    name: 'datasets-list',
    components: {
        'box-container': require('components/containers/box.vue'),
        'dataset-card': require('components/dataset/card.vue')
    },
    data: function() {
        return {
            title: this._('Reused datasets')
        };
    },
    paramAttributes: ['reuse'],
    filters: {
        ids: function(list) {
            return list ? list.map(function(item) {
                return item.id;
            }) : [];
        }
    }
};
</script>
