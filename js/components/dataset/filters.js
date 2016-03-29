import moment from 'moment';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';

export default {
    filters: {
        /**
         * Display a date range in the shorter possible maner.
         */
        daterange: function(range) {
            if (!range || !range.start) {
                return;
            }
            const start = moment(range.start);
            const end = range.end ? moment(range.end) : undefined;
            const start_label = start.format('L');
            const end_label = end.format('L');

            // delta = start.diff(end)
            // delta = value.end - value.start
            // start, end = None, None
            // if start.clone() is_first_year_day(value.start) and is_last_year_day(value.end):
            //     start = value.start.year
            //     if delta.days > 365:
            //         end = value.end.year
            // elif is_first_month_day(value.start) and is_last_month_day(value.end):
            //     start = short_month(value.start)
            //     if delta.days > 31:
            //         end = short_month(value.end)
            // else:
            //     start = short_day(value.start)
            //     if value.start != value.end:
            //         end = short_day(value.end)
            return end_label
                ? this._('{start} to {end}', {start:start_label, end:end_label})
                : start_label;
        },
        frequency_label: function(dataset) {
            if (dataset && dataset.frequency) {
                return frequencies.by_id(dataset.frequency).label;
            }
        },
        granularity_label: function(dataset) {
            if (dataset && dataset.spatial && dataset.spatial.granularity) {
                return granularities.by_id(dataset.spatial.granularity).name;
            }
        }
    }
};
