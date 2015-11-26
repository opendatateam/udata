/*
 * Ensure all community resources have an UUID string as ID
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


var resources = db.community_resource.find(),
    count = 0;

resources.forEach(function(resource) {
    try {
        UUID(resource._id.replace(/-/g, ''));
    } catch (e) {
        resource._id = uuid();
        db.community_resources.save(resource);
        count++;
    }
});

print('Migrated '+count+' community resource(s)');
