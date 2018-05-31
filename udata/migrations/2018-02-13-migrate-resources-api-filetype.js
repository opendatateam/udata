/*
 * Migrate resources where `filetype` is `api` to `filetype = remote` and
 * `type = api`.
 */

var nbMigrated = 0;

db.dataset.find({
    'resources.filetype': 'api',
}).forEach(dataset => {
    dataset.resources.forEach(resource => {
        if (resource.filetype === 'api') {
            resource.filetype = 'remote';
            resource.type = 'api';
            nbMigrated++;
        }
    });
    db.dataset.save(dataset);
});

print(`Migrated ${nbMigrated} resource(s) with an API filetype.`);
