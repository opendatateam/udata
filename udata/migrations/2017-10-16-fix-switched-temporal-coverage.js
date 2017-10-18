/*
 * Ensure all datasets have positive temporal coverage
 */

var modified = 0;

db.dataset.aggregate([
     {$project: {_id: true, temporal_coverage: true, reversed: {$cmp: ['$temporal_coverage.start','$temporal_coverage.end']}}},
     {$match: {reversed:  1}}
]).forEach(function({_id, temporal_coverage}) {
    modified += db.dataset.update({_id}, {$set: {temporal_coverage: {
        start: temporal_coverage.end,
        end: temporal_coverage.start
    }}}).nModified;
});

print(`${modified} datasets had reserved temporal coverage.`);
