/*
 * Update spatial granularities with French names.
 *
 */

var result = db.dataset.update(
    {'spatial.granularity': 'fr/town'},
    {$set: {'spatial.granularity': 'fr/commune'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for towns.');

result = db.dataset.update(
    {'spatial.granularity': 'fr/county'},
    {$set: {'spatial.granularity': 'fr/departement'}},
    {multi: true}
);
print(result.nModified, 'datasets granularity modified for counties.');
