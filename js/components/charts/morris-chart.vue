<style lang="less">
.chart {
    .morris-hover {
          &.morris-default-style {
            color: #f9f9f9;
            background: rgba(0, 0, 0, 0.8);
            border: solid 2px rgba(0, 0, 0, 0.9);
          }
    }
}
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
                    v-class="active: charttype == $key"
                    aria-pressed="{{charttype == $key}}"
                    v-on="click: charttype = $key"
                    >
                    <span class="fa fa-fw fa-{{$value}}"></span>
                </button>
            </div>
        </aside>
        <div class="chart" v-style="height: height || '300 px'"></div>
    </box-container>
</template>

<script>
'use strict';

var $ = require('jquery'),
    moment = require('moment'),
    debounce = require('debounce'),
    Morris = require('shims/morris');

module.exports = {
    name: 'morris-chart',
    data: function() {
        return {
            chart: null,
            charttype: 'Area',
            types: {
                Area: 'area-chart',
                Bar: 'bar-chart',
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
        this.build_chart();
        this.cb = function() {
            if (this.chart) {
                this.chart.setData(this.metrics.series);
            }
        }.bind(this);
        this.metrics.$on('updated', this.cb);

        this.resize_cb = debounce(function() {
            if (this.chart) {
                this.chart.resizeHandler();
            }
        }.bind(this), 200);
        $(window).on('resize', this.resize_cb);
    },
    beforeDestroy: function() {
        this.metrics.$off('updated', this.cb);
        $(window).off('resize', this.resize_cb);
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

            this.clean_chart();
            this.chart = new Morris[this.charttype]({
                element: this.chart_el,
                resize: false,
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
        },
        clean_chart: function() {
            if (this.chart) {
                delete this.chart.handlers.click;
                delete this.chart.handlers.gridclick;
                $(this.chart_el).empty();
            }
        }
    }
};
</script>
