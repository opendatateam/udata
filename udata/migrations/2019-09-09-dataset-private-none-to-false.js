/*
 * Migrate datasets where `private` is `None` to `private = False`
 */

var nbMigrated = 0;

db.dataset.find({
    private: null,
}).forEach(dataset => {
    dataset.private = false;
    db.dataset.save(dataset);
    nbMigrated++;
});

print(`Migrated ${nbMigrated} datasets with private=None.`);
