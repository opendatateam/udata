/*
 * Ensure all resources with checksum have a checksum type
 */

var datasets = db.dataset.find({
    'resources.checksum.value': {$exists: true},
    'resources.checksum.type': {$exists: false}
});

print('Candidates: ' + datasets.count());

var counter = 0;
var count = 0;

datasets.forEach(function(dataset) {
    var resources = dataset.resources.map(function(resource) {
        if (resource.checksum && resource.checksum.value && !resource.checksum.type) {
            resource.checksum.type = 'sha1';
            count++;
        }
        return resource;
    });
    var result = db.dataset.update({_id: dataset._id},
                                   {$set: {resources: resources}});
    counter += result.nModified;
});
print(count, 'resources modified.');
print(counter, 'datasets modified.');
