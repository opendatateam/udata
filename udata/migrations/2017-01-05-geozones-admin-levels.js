/*
 * Affect admin levels to extra-country levels
 */

const ADMIN_LEVELS = {
    'country': 20,
    'country-group': 10,
    'country-subset': 30
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
