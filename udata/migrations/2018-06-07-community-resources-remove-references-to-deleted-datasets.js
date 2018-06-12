/**
 * Delete references to deleted datasets from CommunityResources
 */

var deleted = 0;

db.community_resource.find().forEach(function(resource) {
    var cursor = db.dataset.find({'_id' : resource.dataset});
    if (cursor.hasNext() == false) {
        db.community_resource.update(
            {_id: resource._id},
            {$unset: {dataset: true}}
        );
        deleted++;
    }
});

print(`${deleted} community resources' dataset references removed.`);
