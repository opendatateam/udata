/*
 * Update spatial zones with French names.
 *
 */

var datasets = db.dataset.find({
    'spatial.granularity': 'fr/commune'
});

var counter = 0;

datasets.forEach(function (dataset) {
    var hasChanged = false;
    var oldZones = dataset.spatial.zones;
    if (!oldZones) return
    var newZones = oldZones.map(function (zone) {
        if (zone.startsWith('fr/town')) {
            ;[country, town, id] = zone.split('/');
            zone = country + '/commune/' + id;
            hasChanged = true;
        }
        return zone;
    });
    if (hasChanged) {
        var result = db.dataset.update({_id: dataset._id},
                                       {$set: {'spatial.zones': newZones}});
        counter += result.nModified;
    }
});
print(counter, 'datasets zones modified for communes.');

datasets = db.dataset.find({
    'spatial.granularity': 'fr/departement'
});

counter = 0;

datasets.forEach(function (dataset) {
    var hasChanged = false;
    var oldZones = dataset.spatial.zones;
    if (!oldZones) return
    var newZones = oldZones.map(function (zone) {
        if (zone.startsWith('fr/county')) {
            ;[country, town, id] = zone.split('/');
            zone = country + '/departement/' + id;
            hasChanged = true;
        }
        return zone;
    });
    if (hasChanged) {
        var result = db.dataset.update({_id: dataset._id},
                                       {$set: {'spatial.zones': newZones}});
        counter += result.nModified;
    }
});
print(counter, 'datasets zones modified for departements.');
