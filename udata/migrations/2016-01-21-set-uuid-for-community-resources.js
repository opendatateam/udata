/*
 * Ensure all community resources have an UUID string as ID
 * Migration 2015-11-23 was useless given that it was saved
 * within a new table. Oops.
 */

/**
 * Generate a rfc4122 version 4 UUID
 */
function uuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
}

var resources = db.community_resource.find();
var count = 0;

resources.forEach(function(resource) {
    try {
        UUID(resource._id.replace(/-/g, ''));
    } catch (e) {
        var initialId = resource._id;
        resource._id = uuid();
        // Create a new resource with the new uuid.
        db.community_resource.save(resource);
        // Then delete the old one, you can't modify an ID with mongo?
        db.community_resource.remove({_id: initialId});
        count++;
    }
});

print('Migrated '+count+' community resource(s)');

db.community_resources.drop();
print('Useless community resources database droped.');
