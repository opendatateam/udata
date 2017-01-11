/*
 * Map some old frequencies to new Dublin Core ones
 */

const FREQUENCIES = {
    'fortnighly': 'biweekly',
    'biannual': 'semiannual',
    'realtime': 'continuous'
};

for (var old in FREQUENCIES) {
    const result = db.dataset.update(
        {frequency: old},
        {$set: {frequency: FREQUENCIES[old]}},
        {multi: true}
    );

    print(`Migrated ${result.nModified} dataset from '${old}' to '${FREQUENCIES[old]}' frequency`);
}
