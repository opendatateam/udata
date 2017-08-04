/*
 * Update spatial granularities with French names.
 *
 */

var result = db.dataset.update(
    {'spatial.granularity': 'fr/town'},
    {$set: {'spatial.granularity': 'fr:commune'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:commune.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/county'},
    {$set: {'spatial.granularity': 'fr:departement'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:departement.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/region'},
    {$set: {'spatial.granularity': 'fr:region'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:region.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/district'},
    {$set: {'spatial.granularity': 'fr:arrondissement'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:arrondissement.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/epci'},
    {$set: {'spatial.granularity': 'fr:epci'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:epci.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/canton'},
    {$set: {'spatial.granularity': 'fr:canton'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:canton.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/iris'},
    {$set: {'spatial.granularity': 'fr:iris'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for fr:iris.');
