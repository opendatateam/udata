/*
 * Ensure all resources with checksum have a checksum type
 *
 * Same migration as udata:2016-01-25-fix-resources-checksums.js just optimized.
 *
 * Needed to reapply because of https://github.com/etalab/udata/pull/328
 * not fixing the creation case  and data corruption was still happening
 * until https://github.com/etalab/udata/pull/371
 */

var datasets = db.dataset.find({
    resources: {$elemMatch: {
        'checksum.value': {$exists: true},
        'checksum.type': {$exists: false}
    }}
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
