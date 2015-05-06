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
            timeserie: function() {
                if (!this.items || !this.start || !this.end) {
                    return [];
                }

                var names = arguments,
                    start = moment(this.start),
                    end = moment(this.end),
                    days = end.diff(start, 'days'),
                    // previous = {},
                    data = [],
                    dict = {};

                // Extract values
                for (var i=0; i < this.items.length; i++) {
                    var item = this.items[i];
                    dict[item.date] = item.values;
                }

                for (i=0; i <= days; i++) {
                    var date = start.clone().add(i, 'days'),
                        key = date.format('YYYY-MM-DD'),
                        row = {date: key};

                    for (var j=0; j <= names.length; j++) {
                        var name = names[j];

                        if (dict.hasOwnProperty(key) && dict[key].hasOwnProperty(name)) {
                            row[name] = dict[key][name];
                        } else {
                            row[name] = 0; // TODO provide more fallback mecanisms
                        }
                    }

                    data.push(row);
                }

                return data;
            }
        }
    });

    return Metrics;
});
