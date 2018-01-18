/*
 * Remove checksum from resources where it has no value
 */

var nbCleaned = 0;

db.dataset.find({
    'resources.checksum': {$exists: true},
    'resources.checksum.value': {$exists: false},
}).forEach(dataset => {
    dataset.resources.forEach(resource => {
        if (resource.checksum && !resource.checksum.value) {
            delete resource.checksum;
            nbCleaned++;
        }
    });
    db.dataset.save(dataset);
});

print(`Cleaned ${nbCleaned} resource(s) with an unvalid checksum field.`);
