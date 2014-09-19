define([
    'jquery',
    'api',
    'logger',
    'moment',
    'chart/bar',
    'chart/line',
    'chart/timeserie',
    'chart/radar'
], function($, API, log, moment, BarChart, LineChart, TimeSerie, RadarChart) {
    'use strict';

    var today = moment(),
        last_week = moment().subtract(10, 'days'),
        url = '/metrics/site';

    url += '?' + $.param({start: last_week.format('YYYY-MM-DD'), end: today.format('YYYY-MM-DD')});

    function load_metrics() {
        log.debug('Fetching metrics');
        API.get(url, function(data) {
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

    return {
        start: function() {
            load_metrics();
        }
    };
});


