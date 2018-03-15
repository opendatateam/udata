/*
 * Ensure validityless zones are properly stored
 */

const result = db.geo_zone.update(
    {validity: {}},
    {$unset: {validity: true}},
    {multi: true}
);

print(`Updated ${result.nModified} zones`);
