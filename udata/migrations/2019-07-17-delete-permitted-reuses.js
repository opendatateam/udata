/*
 * Cleanup permitted_reuses metric
 * See: https://github.com/opendatateam/udata/pull/2244
 */

var result = db.organization.update(
    {'metrics.permitted_reuses': {$exists: true}},
    {$unset: {'metrics.permitted_reuses': true}},
    {multi: true}
);
print(result.nModified, 'organizations cleaned (removed metrics.permitted_reuses attribute).');


result = db.metrics.update(
    {'values.permitted_reuses': {$exists: true}},
    {$unset: {'values.permitted_reuses': true}},
    {multi: true}
);
print(result.nModified, 'metrics cleaned (removed values.permitted_reuses attribute).');
