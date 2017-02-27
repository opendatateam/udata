/*
 * Manually created indexes that can't be expressed with mongoengine
 */

// Index on discussion.subject.id with and without default order
db.discussion.createIndex({'subject._ref.$id': 1});
db.discussion.createIndex({'subject._ref.$id': 1, 'created': -1});
print('Created missing indexes on db.discussion');

// Index on issue.subject.id with and without default order
db.issue.createIndex({'subject._ref.$id': 1});
db.issue.createIndex({'subject._ref.$id': 1, 'created': -1});
print('Created missing indexes on db.issue');
