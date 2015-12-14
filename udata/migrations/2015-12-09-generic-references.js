/*
 * Migrate disucssions and issues to DBRef/GenericReferenceField
 */

/**
 * Maps inherited classes to theiru subject collection
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
};

var CLASSES = {
    'dataset': 'Dataset',
    'reuse': 'Reuse',
    'organization': 'Organization',
    'user': 'User'
};

/**
 * Produce a (wweird) GenericReferenceField from a class and an ID
 */
function ref(cls, id) {
    cls = TYPES[cls];
    return {
        _cls: CLASSES[cls],
        _ref: {$ref: cls, $id: id}
    };
}

var discussions = db.discussion.find();
print('Processing ' + discussions.count() + ' discussions');
discussions.forEach(function(discussion) {
    db.discussion.update({_id: discussion._id}, {
        $unset: {_cls: true},
        $set: {subject: ref(discussion._cls, discussion.subject)}
    });
});

var issues = db.issue.find();
print('Processing ' + issues.count() + ' issues');
issues.forEach(function(issue) {
    db.issue.update({_id: issue._id}, {
        $unset: {_cls: true},
        $set: {subject: ref(issue._cls, issue.subject)}
    });
});

var follows = db.follow.find();
print('Processing ' + follows.count() + ' follows');
follows.forEach(function(follow) {
    db.follow.update({_id: follow._id}, {
        $unset: {_cls: true},
        $set: {following: ref(follow._cls, follow.following)}
    });
});
