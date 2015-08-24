define([
    'jquery',
    'api.light',
    'logger',
    'moment',
    'chart/bar',
    'chart/line',
    'chart/timeserie',
    'widgets/follow-btn'
], function($, API, log, moment, BarChart, LineChart, TimeSerie) {
    'use strict';

    var today = moment(),
        last_week = moment().subtract(10, 'days'),
        org_id = $('[data-organization-id]').data('organization-id'),
        url = '/metrics/' + org_id;

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

    $(function() {
        log.debug('Start organization dashboard view');
        load_metrics();
    });
});


