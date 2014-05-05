define([
    'jquery',
    'logger',
    'moment',
    'chart/bar',
    'chart/line',
    'chart/timeserie',
    'chart/radar'
], function($, log, moment, BarChart, LineChart, TimeSerie, RadarChart) {
    'use strict';

    var today = moment(),
        last_week = moment().subtract('days', 7),
        url = '/api/metrics/site/';

    url += last_week.format('YYYY-MM-DD') + '+' + today.format('YYYY-MM-DD');

    function start() {
        log.debug('Fetching metrics');
        $.get(url, function(data) {
            log.debug('Metrics fetched:', data);

            $('[data-chart-type="line"]').each(function() {
                var $this = $(this),
                    serie = TimeSerie.extract(data, $this.data('chart-data'));

                new LineChart($this).draw(serie.getLasts(5));
            });

            $('[data-chart-type="bar"]').each(function() {
                var $this = $(this),
                    serie = TimeSerie.extract(data, $this.data('chart-data'));

                new BarChart($this).draw(serie.getLasts(10));
            });
        });

    }

    return {start: start};
});


