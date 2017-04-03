/*
 * Affect admin levels to french levels
 */

const ADMIN_LEVELS = {
    'fr/region': 40,
    'fr/county': 60,
    'fr/epci': 68,
    'fr/district': 70,
    'fr/town': 80,
    'fr/canton': 98,
    'fr/iris': 98,
};

var nb = 0;

for (var key in ADMIN_LEVELS) {
    const result = db.geo_level.update(
        {_id: key},
        {$set: {admin_level: ADMIN_LEVELS[key]}}
    );
    nb += result.nModified;
}
print(`Affected admin level to ${nb} geospatial level`);
