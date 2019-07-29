/**
 * Swap reversed DateRange values
 */

var updated = 0;

// Match all Dataset having temporal_coverage.start > temporal_coverage.end
const pipeline = [
    {$project: {
        cmp: {$cmp: ['$temporal_coverage.start', '$temporal_coverage.end']},
        dataset: '$$ROOT'
    }},
    {$match: {cmp: {$gt: 0}}}
];


db.dataset.aggregate(pipeline).forEach(row => {
    db.dataset.update(
        {_id: row.dataset._id},
        {'$set': {
            'temporal_coverage.start': row.dataset.temporal_coverage.end,
            'temporal_coverage.end': row.dataset.temporal_coverage.start,
        }}
    );
    updated++;
});

print(`Updated ${updated} datasets with reversed temporal coverage.`);
