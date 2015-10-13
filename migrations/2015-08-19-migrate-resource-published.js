var datasets = db.dataset.find();
var counter = 0;
var commonDate = new ISODate("2014-09-04");

datasets.map(function(dataset) {
    if (dataset.resources) {
        var resources = dataset.resources.map(function(resource) {
            // Some published date are undefined.
            var published = resource.published || commonDate;
            if (published.toDateString() === commonDate.toDateString()) {
                resource.published = resource.created_at;
            }
            return resource;
        });
        var result = db.dataset.update({_id: dataset._id},
                                        {$set: {resources: resources}});
        counter += result.nModified;
    }
});
print(counter, 'datasets modified.');
