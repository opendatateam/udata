/*
 * Update spatial granularities with French names.
 *
 */

var datasets = db.dataset.find({
    'spatial.granularity': 'fr/town'
});

print('Candidates: ' + datasets.count());

var counter = 0;

datasets.forEach(function (dataset) {
    var result = db.dataset.update({_id: dataset._id},
                                   {$set: {'spatial.granularity': 'fr/commune'}});
    counter += result.nModified;
});
print(counter, 'datasets granularity modified for towns.');

datasets = db.dataset.find({
    'spatial.granularity': 'fr/commune'
});

counter = 0;

datasets.forEach(function (dataset) {
    var oldZones = dataset.spatial.zones;
    if (!oldZones) return
    var newZones = oldZones.map(function (zones) {
        if (typeof zones === 'string') {
            zones = [zones]
        }
        var newZone = zones.map(function (zone) {
            if (zone.startsWith('fr/town')) {
                ;[country, town, id] = zone.split('/');
                zone = country + '/commune/' + id;
            }
            return zone;
        });
        return newZone;
    });
    var result = db.dataset.update({_id: dataset._id},
                                   {$set: {'spatial.zones': newZones}});
    counter += result.nModified;
});
print(counter, 'datasets zones modified for communes.');

datasets = db.dataset.find({
    'spatial.granularity': 'fr/county'
});

counter = 0;

datasets.forEach(function (dataset) {
    var result = db.dataset.update({_id: dataset._id},
                                   {$set: {'spatial.granularity': 'fr/departement'}});
    counter += result.nModified;
});
print(counter, 'datasets granularity modified for counties.');

datasets = db.dataset.find({
    'spatial.granularity': 'fr/departement'
});

counter = 0;

datasets.forEach(function (dataset) {
    var oldZones = dataset.spatial.zones;
    if (!oldZones) return
    var newZones = oldZones.map(function (zones) {
        if (typeof zones === 'string') {
            zones = [zones]
        }
        var newZone = zones.map(function (zone) {
            if (zone.startsWith('fr/county')) {
                ;[country, town, id] = zone.split('/');
                zone = country + '/departement/' + id;
            }
            return zone;
        });
        return newZone;
    });
    var result = db.dataset.update({_id: dataset._id},
                                   {$set: {'spatial.zones': newZones}});
    counter += result.nModified;
});
print(counter, 'datasets zones modified for departements.');
