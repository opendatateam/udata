var datasets = db.dataset.find();
var communityResources = db.community_resource.find();
var counter = 0;
var resourceCounter = 0;
var communityResourceCounter = 0;

datasets.map(function(dataset) {
    if (dataset.resources) {
        var resources = dataset.resources.map(function(resource) {
            resource.filetype = resource.type;
            delete resource.type;
            if (typeof resource.size !== undefined) {
                resource.filesize = resource.size;
                delete resource.size;
                resourceCounter += 1;
            }
            return resource;
        });
        var result = db.dataset.update({_id: dataset._id},
                                        {$set: {resources: resources}});
        counter += result.nModified;
    }
});
print(counter, 'datasets modified.');
print(resourceCounter, 'resources sizes modified.');

communityResources.map(function(communityResource) {
    communityResource.filetype = communityResource.type;
    delete communityResource.type;
    if (typeof communityResource.size !== undefined) {
        communityResource.filesize = communityResource.size;
        delete communityResource.size;
        communityResourceCounter += 1;
    }
    db.community_resource.save(communityResource);
});
print(communityResourceCounter, 'community resources sizes modified.');
print('That migration requires a reindex of datasets.');
