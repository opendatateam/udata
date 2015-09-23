var datasets = db.dataset.find();
var counter = 0;
var resourceCounter = 0;

datasets.map(function(dataset) {
    if (dataset.community_resources) {
        dataset.community_resources.map(function(community_resource) {
            community_resource.dataset = dataset._id;
            community_resource._id = community_resource.id;
            delete community_resource.id;
            db.community_resource.save(community_resource);
            resourceCounter += 1;
        });
        var result = db.dataset.update({_id: dataset._id},
                                       {$unset: {community_resources: true}});
        counter += result.nModified;
    }
});
print(counter, 'datasets modified.');
print(resourceCounter, 'community resources created.');
