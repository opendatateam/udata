/*
 * Update spatial granularities with French names.
 *
 */

var result = db.dataset.update(
    {'spatial.granularity': 'fr/town'},
    {$set: {'spatial.granularity': 'fr:commune'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for towns.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/county'},
    {$set: {'spatial.granularity': 'fr:departement'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for counties.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/region'},
    {$set: {'spatial.granularity': 'fr:region'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for regions.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/district'},
    {$set: {'spatial.granularity': 'fr:district'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for districts.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/epci'},
    {$set: {'spatial.granularity': 'fr:epci'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for epcis.');
