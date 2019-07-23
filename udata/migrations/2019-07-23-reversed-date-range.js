/**
 * Swap reversed DateRange values
 */

var updated = 0;

// Match all Dataset having temporal_coverage.start > temporal_coverage.end
const pipeline = [
    {$project: {
        cmp: {$cmp: ['$temporal_coverage.start', '$temporal_coverage.end']},
        obj: '$$ROOT'
    }},
    {$match: {cmp: {$gt: 0}}},
    {$replaceRoot: {newRoot: '$obj'}}
];


db.dataset.aggregate(pipeline).forEach(dataset => {
    db.dataset.update(
        {_id: dataset._id},
        {'$set': {
            'temporal_coverage.start': dataset.temporal_coverage.end,
            'temporal_coverage.end': dataset.temporal_coverage.start,
        }}
    );
    updated++;
});

print(`Updated ${updated} datasets with reversed temporal coverage.`);
