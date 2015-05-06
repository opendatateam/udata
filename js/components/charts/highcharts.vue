<style lang="less">
// .chart {
//     .morris-hover {
//           &.morris-default-style {
//             color: #f9f9f9;
//             background: rgba(0, 0, 0, 0.8);
//             border: solid 2px rgba(0, 0, 0, 0.9);
//           }
//     }
// }
</style>

<template>
    <box-container title="{{title}}" icon="{{ icon || 'line-chart' }}"
        boxclass="box-solid"
        bodyclass="chart-responsive"
        loading="{{metrics.loading}}">
        <aside>
            <div class="btn-group" data-toggle="btn-toggle">
                <button type="button" class="btn btn-primary btn-xs"
                    v-repeat="types"
                    v-class="active: charttype == $value"
                    aria-pressed="{{charttype == $value}}"
                    v-on="click: charttype = $value"
                    >{{$value}}</button>
            </div>
        </aside>
        <div class="chart" v-style="height: height || '300 px'"></div>
    </box-container>
</template>

<script>
'use strict';

var $ = require('jquery'),
    moment = require('moment'),
    Highcharts = require('imports?$=jquery,window=>{}!exports?window.Highcharts!highcharts'),
    options = {
        chart: {
            type: 'area'
        },
        title: {
            text: 'Historic and Estimated Worldwide Population Growth by Region'
        },
        subtitle: {
            text: 'Source: Wikipedia.org'
        },
        xAxis: {
            categories: ['1750', '1800', '1850', '1900', '1950', '1999', '2050'],
            tickmarkPlacement: 'on',
            title: {
                enabled: false
            }
        },
        yAxis: {
            title: {
                text: 'Billions'
            },
            labels: {
                formatter: function () {
                    return this.value / 1000;
                }
            }
        },
        tooltip: {
            shared: true,
            valueSuffix: ' millions'
        },
        plotOptions: {
            area: {
                stacking: 'normal',
                lineColor: '#666666',
                lineWidth: 1,
                marker: {
                    lineWidth: 1,
                    lineColor: '#666666'
                }
            }
        },
        series: [{
            name: 'Asia',
            data: [502, 635, 809, 947, 1402, 3634, 5268]
        }, {
            name: 'Africa',
            data: [106, 107, 111, 133, 221, 767, 1766]
        }, {
            name: 'Europe',
            data: [163, 203, 276, 408, 547, 729, 628]
        }, {
            name: 'America',
            data: [18, 31, 54, 156, 339, 818, 1201]
        }, {
            name: 'Oceania',
            data: [2, 2, 2, 6, 13, 30, 46]
        }]
    };

module.exports = {
    name: 'high-charts',
    data: function() {
        return {
            chart: null,
            charttype: 'Area',
            types: ['Area', 'Bar', 'Line']
        };
    },
    paramAttributes: [
        'title',
        'icon',
        'default',
        'height',
        'x',
        'y',
        'metrics'
    ],
    computed: {
        chart_el: function() {
            return $(this.$el).find('.chart')[0];
        },
        fields: function() {
            return $.map(this.y, function(item) {
                return item.id;
            });
        },
        labels: function() {
            return $.map(this.y, function(item) {
                return item.label;
            });
        },
        colors: function() {
            return $.map(this.y, function(item) {
                return item.color;
            });
        }
    },
    components: {
        'box-container': require('components/containers/box.vue')
    },
    ready: function() {
        this.chart = Highcharts.Chart(options);
        // this.build_chart();
        // this.metrics.$on('updated', function() {
        //     if (this.chart) {
        //         this.chart.setData(this.metrics.series);
        //     }
        // }.bind(this));
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

            if (this.chart) {
                $(this.chart_el).empty();
            }

            this.chart = new Morris[this.charttype]({
                element: this.chart_el,
                resize: true,
                data: this.metrics.series,
                xkey: this.x,
                ykeys: this.fields,
                labels: this.labels,
                lineColors: this.colors,
                hideHover: 'auto',
                xLabelFormat: function(date) {
                    return moment(date).format('L');
                },
                dateFormat: function(date) {
                    return moment(date).format('L');
                }
            });
        }
    }
};
</script>
