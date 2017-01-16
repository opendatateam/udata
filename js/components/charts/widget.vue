<style lang="less">
.chart-legend {
    text-align: center;
    margin-top: 10px;

    ul {
        list-style: none;
        margin-bottom: 0;

        li {
            display: inline-block;
            margin-right: 5px;

            span {
                display: inline-block;
                width: 20px;
                height: 16px;
                margin-right: 5px;
                margin-left: 10px;
                border: 1px solid #999;
                vertical-align: middle;
            }
        }

    }
}
</style>

<template>
    <box :title="title" :icon="icon"
        boxclass="box-solid"
        bodyclass="chart-responsive"
        :loading="metrics.loading">
        <div class="chart" :style="{height: height}" v-el:container>
            <canvas v-el:canvas height="100%"></canvas>
        </div>
        <div class="chart-legend" v-el:legend></div>
    </box>
</template>

<script>
import $ from 'jquery';
import moment from 'moment';
import Chart from 'chart.js';
import 'Chart.StackedBar.js';

/*
 * Set common global chart options
 */
Chart.defaults.global.showScale = true;
Chart.defaults.global.scaleLineColor = 'rgba(0,0,0,.05)';
Chart.defaults.global.scaleLineWidth = 1;
Chart.defaults.global.responsive = true;
Chart.defaults.global.maintainAspectRatio = false;
Chart.defaults.global.multiTooltipTemplate = '<%=datasetLabel%>: <%= value %>';


const AREA_OPTIONS = {
    // scaleShowGridLines: false,
    scaleShowHorizontalLines: true,
    scaleShowVerticalLines: true,
    bezierCurveTension: 0.3,
};
const LINE_OPTIONS = $.extend({}, AREA_OPTIONS, {
    datasetFill: false,
});
const BAR_OPTIONS = {
    scaleBeginAtZero: true,
    scaleShowGridLines: true,
    scaleShowHorizontalLines: true,
    scaleShowVerticalLines: true,
    barShowStroke: true,
    barStrokeWidth: 2,
    barValueSpacing: 5,
    barDatasetSpacing: 1,
    datasetFill: false,
};
const STACKEDBAR_OPTIONS = $.extend({}, BAR_OPTIONS, {
    scaleShowVerticalLines: false,
});
const COLORS = [
    '#a0d0e0',
    '#3c8dbc',
    '#4da74d',
    '#ffb311',
    '#8612ee',
    '#aaa',
];


export default {
    name: 'chartjs-chart',
    data: function() {
        return {
            chart: null,
            canvasHeight: null,
        };
    },
    props: {
        title: String,
        icon: {
            type: String,
            default: 'line-chart'
        },
        default: null,
        height: {
            type: String,
            default: '300px'
        },
        x: String,
        y: Array,
        metrics: {
            type: Object,
            required: true
        },
        chartType: {
            type: String,
            default: 'Area'
        }
    },
    computed: {
        series: function() {
            let series = this.y.map((item) => {
                return item.id;
            });
            let raw = this.metrics.timeserie(series);
            let data = {
                labels: raw.map((item) => {
                    return moment(item.date).format('L');
                }),

                datasets: this.y.map((serie, idx) => {
                    let dataset = {label: serie.label};
                    let color = serie.color || COLORS[idx];
                    dataset.fillColor = this.toRGBA(color, .5);
                    dataset.strokeColor = color;
                    dataset.pointColor = color;
                    // datasetpointStrokeColor: "#c1c7d1",
                    dataset.pointHighlightFill = '#fff';
                    dataset.pointHighlightStroke = color;
                    dataset.data = raw.map((item) => {
                        return item[serie.id];
                    });
                    return dataset;
                })
            };

            return data;
        }
    },
    components: {
        box: require('components/containers/box.vue')
    },
    ready: function() {
        this.canvasHeight = this.$els.container.clientHeight;
        this.buildChart();
        this.metrics.$on('updated', this.buildChart.bind(this));
    },
    beforeDestroy: function() {
        this.cleanChart();
    },
    watch: {
        'y': function(new_value, old_value) {
            if (new_value != old_value) {
                this.buildChart();
            }
        }
    },
    methods: {
        buildChart: function() {
            if (!this.y || !this.metrics || !this.chartType) {
                return;
            }
            let factory = this['build' + this.chartType];
            let ctx = this.$els.canvas.getContext('2d');
            this.cleanChart();
            ctx.canvas.height = this.canvasHeight;
            this.chart = factory(ctx);
            this.$els.legend.innerHTML = this.chart.generateLegend();
        },
        buildArea: function(ctx) {
            return new Chart(ctx).Line(this.series, AREA_OPTIONS);
        },
        buildBar: function(ctx) {
            return new Chart(ctx).Bar(this.series, BAR_OPTIONS);
        },
        buildStackedBar: function(ctx) {
            return new Chart(ctx).StackedBar(this.series, STACKEDBAR_OPTIONS);
        },
        buildLine: function(ctx) {
            return new Chart(ctx).Line(this.series, LINE_OPTIONS);
        },
        cleanChart: function() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        },
        toRGBA: function(hex, opacity) {
            // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
            let shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
            hex = hex.replace(shorthandRegex, function(m, r, g, b) {
                return r + r + g + g + b + b;
            });

            let result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ?
                'rgba('
                    + parseInt(result[1], 16) + ','
                    + parseInt(result[2], 16) + ','
                    + parseInt(result[3], 16) + ','
                    + opacity + ')'
                : hex;
        }
    }
};
</script>
