/**
 * An helper module to parse and fix metrics as time series
 */
define(['jquery', 'moment', 'logger'], function($, moment, logger) {

    var LEVELS = {
        daily: {
            key: 'YYYY-MM-DD',
            short: 'L',
            add: function(value, days) {
                return value.add('days', days)
            }
        },
        monthly: {
            key: 'YYYY-MM',
            short: 'MMM. YYYY',
            add: function(value, months) {
                return value.add('months', months)
            }
        }
    };

    function TimeSerie(data, level) {
        level = level || 'daily';

        if (!LEVELS.hasOwnProperty(level)) {
            throw new TypeError('Unknown level "'+ level +'"');
        }

        this.level = LEVELS[level];
        this.data = data;
    };

    TimeSerie.LEVELS = LEVELS;


    TimeSerie.extract = function (data, name, level) {
        var extracted = $.map(data, function(row, idx) {
                return {
                    date: row.date,
                    value: row.values[name]
                }
            });

        return new TimeSerie(extracted, level);
    };

    TimeSerie.prototype = {

        constructor: TimeSerie,

        getLasts: function(nb, default_value) {
            var lasts = [],
                today = moment(),
                first = this.level.add(today.clone(), -nb),
                previous;

            default_value = default_value || 0;

            for (var i=0; i <= nb; i++) {
                var date = this.level.add(first.clone(), i),
                    key = date.format(this.level.key),
                    row = {
                        date: key,
                        label: date.format(this.level.short),
                        value: previous ? previous.value : default_value
                    },
                    match = $.grep(this.data, function(row, idx) {
                        return row.date == key;
                    });


                if (match.length) {
                    row.value = match['0'].value || row.value;
                };

                lasts.push(row);
                previous = row;
            }

            return lasts;
        }
    };

    return TimeSerie;

});
