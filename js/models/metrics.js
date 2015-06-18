define(['api', 'models/base_list', 'vue', 'moment', 'jquery'], function(API, ModelList, Vue, moment, $) {
    'use strict';

    var Metrics = ModelList.extend({
        name: 'Metrics',
        ns: 'site',
        fetch: 'metrics_for',
        data: function() {
            return {
                start: null,
                end: null
            };
        },
        computed: {
            /**
             * Consolidate data
             */
            series: function() {
                if (!this.items) {
                    return [];
                }

                return this.items.map(function(item) {
                    return $.extend({date: item.date}, item.values);
                });
            }
        },
        methods: {
            /**
             * Consolidate data
             */
            timeserie: function(series) {
                if (!this.items || !this.items.length) {
                    return [];
                }

                var first_item = this.items[0],
                    last_item = this.items[this.items.length -1],
                    start = moment(first_item.date),
                    end = moment(last_item.date),
                    days = start.diff(end, 'days'),
                    names = series || Object.keys(last_item.values),
                    data = [],
                    values = {},
                    previous;

                // Extract values
                for (var i=0; i < this.items.length; i++) {
                    var item = this.items[i];
                    values[item.date] = item.values;
                }

                for (i=0; i <= days; i++) {
                    var date = start.clone().add(i, 'days'),
                        key = date.format('YYYY-MM-DD'),
                        row = {date: date, key: key};

                    names.forEach(function(name) {
                        if (values.hasOwnProperty(key) && values[key].hasOwnProperty(name)) {
                            row[name] = values[key][name];
                        } else if (previous.hasOwnProperty(name)) {
                            row[name] = previous[name];
                        } else {
                            row[name] = 0;
                        }
                    });

                    previous = row;
                    data.push(row);
                }

                return data;
            }
        }
    });

    return Metrics;
});
