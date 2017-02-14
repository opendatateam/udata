<style lang="less">
.graphs {
    .graphs-chart .box-title {
        margin-top: 0;
    }
}
</style>
<template>
<div class="graphs">
    <div class="row graphs-chart">
        <chart class="col-xs-12 col-sm-6" :title="_('Latest dataset uploads')"
        :metrics="metrics" icon="null"
        :y="dataDatasets" chart-type="Line"></chart>
        <chart class="col-xs-12 col-sm-6" :title="_('Latest reuse uploads')"
        :metrics="metrics" icon="null"
        :y="dataReuses" chart-type="Line"></chart>
    </div>
</div>
</template>

<script>
import Metrics from 'models/metrics';
import moment from 'moment';
import Chart from 'components/charts/widget.vue';

export default {
    components: {Chart},
    props: ['objectId'],
    data() {
        return {
            metrics: new Metrics({
                data: {
                    loading: true,
                }
            }),
            dataDatasets: [{
                id: 'datasets',
                label: this._('Datasets')
            }],
            dataReuses: [{
                id: 'reuses',
                label: this._('Reuses')
            }]
        };
    },
    watch: {
        objectId(id) {
            this.fetchMetrics();
        }
    },
    attached() {
        this.fetchMetrics();
    },
    methods: {
        fetchMetrics() {
            if (this.objectId) {
                this.metrics.fetch({
                    id: this.objectId,
                    start: moment().subtract(12, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD'),
                    cumulative: false
                });
            }
        }
    }
};
</script>
