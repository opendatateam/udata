/*
 * Ensure all resources have an UUID string as ID
 */

var datasets = db.dataset.find();
var counter = 0;
var count = 0;

datasets.map(function(dataset) {
    if (dataset.resources) {
        var resources = dataset.resources.map(function(resource) {
            if (!resource._id) {
                resource._id = resource.id;
                count++;
            }
            delete resource.id;
            return resource;
        });
        var result = db.dataset.update({_id: dataset._id},
                                        {$set: {resources: resources}});
        counter += result.nModified;
    }
});
print(count, 'resources modified.');
print(counter, 'datasets modified.');
