/*
 * Migrate discussions and issues to DBRef/GenericReferenceField
 */

/**
 * Maps inherited classes to their subject collection
 */
var TYPES = {
    'Discussion.DatasetDiscussion': 'dataset',
    'Discussion.ReuseDiscussion': 'reuse',
    'Issue.DatasetIssue': 'dataset',
    'Issue.ReuseIssue': 'reuse',
    'Follow.FollowDataset': 'dataset',
    'Follow.FollowReuse': 'reuse',
    'Follow.FollowOrg': 'organization',
    'Follow.FollowUser': 'user',
    'Activity.UserCreatedDataset': 'dataset',
    'Activity.UserCreatedOrganization': 'organization',
    'Activity.UserCreatedReuse': 'reuse',
    'Activity.UserFollowedDataset': 'dataset',
    'Activity.UserFollowedOrganization': 'organization',
    'Activity.UserFollowedReuse': 'reuse',
    'Activity.UserFollowedUser': 'user',
    'Activity.UserStarredDataset': 'dataset',
    'Activity.UserUpdatedDataset': 'dataset',
    'Activity.UserUpdatedOrganization': 'organization',
    'Activity.UserUpdatedReuse': 'reuse'
};

/**
 * Maps collections to their classes
 */
var CLASSES = {
    'dataset': 'Dataset',
    'reuse': 'Reuse',
    'organization': 'Organization',
    'user': 'User'
};

/**
 * Process a collection replacing an inheritance pattern with a generic reference.
 * @param  {String} collection The collection name
 * @param  {String} attribute  The attribute to transform into a generic reference
 */
function process(collection, attribute) {
    var objects = db[collection].find(),
        count = 0;
    print('Processing db.' + collection);
    objects.forEach(function(object) {
        if (object._cls) {
            var cls = TYPES[object._cls],
                op = {$unset: {_cls: true}, $set: {}};
            // Build a (weird) GenericReference
            op.$set[attribute] = {
                _cls: CLASSES[cls],
                _ref: {$ref: cls, $id: object[attribute]}
            };
            db[collection].update({_id: object._id}, op);
            count++;
        }
    });
    print('Processed ' + count + ' documents in db.' + collection);
}

process('discussion', 'subject');
process('issue', 'subject');
process('follow', 'following');
