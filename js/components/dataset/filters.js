import moment from 'moment';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';
import resource_types from 'models/resource_types';

export default {
    filters: {
        /**
         * Display a date range in the shorter possible manner.
         */
        daterange(range, details = false) {
            if (!range || !range.start) {
                return;
            }
            const start = moment(range.start);
            const end = range.end ? moment(range.end) : undefined;
            const fmt = details ? 'L' : 'YYYY';
            const start_label = start.format(fmt);
            const end_label = end ? end.format(fmt) : undefined;
            if (details) {
                return end_label
                    ? this._('{start} to {end}', {start: start_label, end: end_label, interpolation: { escapeValue: false }})
                    : start_label;
            } else {
                return end_label && end_label !== start_label ? `${start_label}-${end_label}` : start_label;
            }
        },
        frequency_label(dataset) {
            if (dataset && dataset.frequency) {
                return frequencies.by_id(dataset.frequency).label;
            }
        },
        resource_type_label(resource) {
            if (resource && resource.type) {
                const resource_type = resource_types.by_id(resource.type);
                if (!resource_type) return 'Type not found';
                return resource_type.label;
            }
        },
        granularity_label(dataset) {
            if (dataset && dataset.spatial && dataset.spatial.granularity) {
                return granularities.by_id(dataset.spatial.granularity).name;
            }
        }
    }
};
