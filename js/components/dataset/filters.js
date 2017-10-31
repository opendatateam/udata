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
            const start_label = start.format('YYYY');
            const end_label = end.format('YYYY');

            return end_label
                ? this._('{start_label}-{end_label}', {start_label, end_label})
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
