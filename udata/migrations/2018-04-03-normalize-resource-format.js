/*
 * resource.format: trim and convert to lower case
 */

var count = 0;

function normalizeFormat(resource) {
    if (resource.format) {
        resource.format = resource.format.trim().toLowerCase();
    }
    return resource;
}

db.dataset.find().forEach(function(dataset) {
    if (dataset.resources && dataset.resources.length) {
        const result = db.dataset.update(
            {_id: dataset._id},
            {$set: {resources: dataset.resources.map(normalizeFormat)}}
        );
        count += result.nModified;
    }
});

print(`${count} datasets updated.`);
