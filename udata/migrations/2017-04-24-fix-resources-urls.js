/*
 * Ensure all resources URLs are properly encoded
 */


function fixUrl(url) {
    // Do not process already encoded URLs
    return url && url.indexOf('%') < 0 ? encodeURI(url) : url;
}

function fixResourceUrl(resource) {
    resource.url = fixUrl(resource.url);
    return resource;
}

var count = 0;
const datasets = db.dataset.find({'resources.url': {$exists: true}});

print(`${datasets.count()} datasets to process`);
datasets.forEach(function(dataset) {
    const result = db.dataset.update(
        {_id: dataset._id},
        {$set: {resources: dataset.resources.map(fixResourceUrl)}}
    );
    count += result.nModified;
});
print(`${count} datasets updated.`);


count = 0;
const resources = db.community_resource.find({url: {$exists: true}});

print(`${resources.count()} community resources to process`);
resources.forEach(function(resource) {
    const result = db.community_resource.update(
        {_id: resource._id},
        {$set: {url: fixUrl(resource.url)}}
    );
    count += result.nModified;
});
print(`${count} community resources updated.`);
