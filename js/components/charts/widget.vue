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
    <box title="{{title}}" icon="{{ icon || 'line-chart' }}"
        boxclass="box-solid"
        bodyclass="chart-responsive"
        loading="{{metrics.loading}}">
        <aside>
            <div class="btn-group" data-toggle="btn-toggle">
                <button type="button" class="btn btn-primary btn-xs"
                    v-repeat="types"
                    v-class="active: charttype == $key"
                    aria-pressed="{{charttype == $key}}"
                    v-on="click: charttype = $key"
                    >
                    <span class="fa fa-fw fa-{{$value}}"></span>
                </button>
            </div>
        </aside>
        <div class="chart" v-style="height: height" v-el="container">
            <canvas v-el="canvas" height="100%"></canvas>
        </div>
        <div class="chart-legend" v-el="legend"></div>
    </box>
</template>

<script>
'use strict';

var $ = require('jquery'),
    moment = require('moment'),
    debounce = require('debounce'),
    Chart = require('chart.js');

require('Chart.StackedBar.js');

/*
 * Set common global chart options
 */
Chart.defaults.global.showScale = true;
Chart.defaults.global.scaleLineColor = 'rgba(0,0,0,.05)';
Chart.defaults.global.scaleLineWidth = 1;
Chart.defaults.global.responsive = true;
Chart.defaults.global.maintainAspectRatio = false;
Chart.defaults.global.multiTooltipTemplate = '<%=datasetLabel%>: <%= value %>';


var AREA_OPTIONS = {
        // scaleShowGridLines: false,
        scaleShowHorizontalLines: true,
        scaleShowVerticalLines: true,
        bezierCurveTension: 0.3,
    },

    LINE_OPTIONS = $.extend({}, AREA_OPTIONS, {
        datasetFill: false
    }),

    BAR_OPTIONS = {
        scaleBeginAtZero: true,
        scaleShowGridLines: true,
        scaleShowHorizontalLines: true,
        scaleShowVerticalLines: true,
        barShowStroke: true,
        barStrokeWidth: 2,
        barValueSpacing: 5,
        barDatasetSpacing: 1,
        datasetFill: false
    },
    COLORS = [
        '#a0d0e0',
        '#3c8dbc',
        '#4da74d',
        '#ffb311',
        '#8612ee',
        '#aaa',
    ];


module.exports = {
    name: 'chartjs-chart',
    data: function() {
        return {
            chart: null,
            charttype: 'Area',
            canvasHeight: null,
            height: '300px',
            types: {
                Area: 'area-chart',
                Bar: 'bar-chart',
                StackedBar: 'bar-chart',
                Line: 'line-chart'
            }
        };
    },
    props: [
        'title',
        'icon',
        'default',
        'height',
        'x',
        'y',
        'metrics'
    ],
    computed: {
        series: function() {
            var series = this.y.map(function(item) {
                    return item.id;
                }),
                raw = this.metrics.timeserie(series),
                data = {
                    labels: raw.map(function(item) {
                        return moment(item.date).format('L');
                    }),

                    datasets: this.y.map(function(serie, idx) {
                        var dataset = {label: serie.label},
                            color = serie.color || COLORS[idx];
                        dataset.fillColor = this.toRGBA(color, .5);
                        dataset.strokeColor = color;
                        dataset.pointColor = color;
                        // datasetpointStrokeColor: "#c1c7d1",
                        dataset.pointHighlightFill = '#fff';
                        dataset.pointHighlightStroke = color;
                        dataset.data = raw.map(function(item) {
                            return item[serie.id];
                        });
                        return dataset;
                    }.bind(this))
                };

            return data;
        }
    },
    components: {
        'box': require('components/containers/box.vue')
    },
    ready: function() {
        this.canvasHeight = this.$$.container.clientHeight;
        this.build_chart();
        this.metrics.$on('updated', this.build_chart.bind(this));
    },
    beforeDestroy: function() {
        this.clean_chart();
    },
    watch: {
        'y': function(new_value, old_value) {
            if (new_value != old_value) {
                this.build_chart();
            }
        },
        'charttype': function() {
            this.build_chart();
        }
    },
    methods: {
        build_chart: function() {
            if (!this.y || !this.metrics || !this.charttype) {
                return;
            }

            var factory = this['build' + this.charttype],
                ctx = this.$$.canvas.getContext('2d');

            this.clean_chart();
            ctx.canvas.height = this.canvasHeight;
            this.chart = factory(ctx);
            this.$$.legend.innerHTML = this.chart.generateLegend();
        },
        buildArea: function(ctx) {
            return new Chart(ctx).Line(this.series, AREA_OPTIONS);
        },
        buildBar: function(ctx) {
            return new Chart(ctx).Bar(this.series, BAR_OPTIONS);
        },
        buildStackedBar: function(ctx) {
            return new Chart(ctx).StackedBar(this.series, BAR_OPTIONS);
        },
        buildLine: function(ctx) {
            return new Chart(ctx).Line(this.series, LINE_OPTIONS);
        },
        clean_chart: function() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        },
        toRGBA: function(hex, opacity) {
            // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
            var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
            hex = hex.replace(shorthandRegex, function(m, r, g, b) {
                return r + r + g + g + b + b;
            });

            var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
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
