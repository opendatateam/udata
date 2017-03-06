/*
 * Remove harvest sources owner when there is an orgnization
 */
const result = db.harvest_source.update(
    {owner: {$exists: true}, organization: {$exists: true}},
    {$unset: {owner: true}},
    {multi: true}
);

print(`Updated ${result.nModified} harvest source(s) with both owner and organization`);
