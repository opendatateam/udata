/*
 * Deduplicate users by their email.
 *
 * Only one user is kept.
 * Others' ressources (ie.datasets, reuses, memberships, followers...)
 * are moved to the kept user
 *
 * A reindexation is necessary after this migration
 */

/**
 * Reaffect datasets from sources to target
 * @param  {User} target  The target user receiving all the datasets
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected datasets
 */
function reaffectDatasets(target, sources) {
    return db.dataset.update(
        {owner: {$in: sources}},
        {$set: {owner: target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Reaffect organization memberships from sources to target
 * @param  {User} target  The target user receiving all the memberships
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected memberships
 */
function affectToOrganizations(target, sources) {
    return db.organization.update(
        {'members.user': {$in: sources}},
        {$set: {'members.$.user': target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Reaffect reuses from sources to target
 * @param  {User} target  The target user receiving all the reuses
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected reuses
 */
function reaffectReuses(target, sources) {
    return db.reuse.update(
        {owner: {$in: sources}},
        {$set: {owner: target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Reaffect folowers from sources to target
 * @param  {User} target  The target user receiving all the folowers
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected folowers
 */
function reaffectFollowers(target, sources) {
    return db.follow.update(
        {following: {$in: sources}},
        {$set: {following: target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Reaffect subscription from sources to target
 * @param  {User} target  The target user receiving all the subscriptions
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected subscriptions
 */
function reaffectSubsriptions(target, sources) {
    return db.follow.update(
        {follower: {$in: sources}},
        {$set: {follower: target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Reaffect discussions from sources to target
 * @param  {User} target  The target user receiving all the discussions
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected discussions
 */
function reaffectDiscussions(target, sources) {
    var nb = 0;
    db.discussion.find({$or: [
        {user: {$in: sources}},
        {'discussion.posted_by': {$in: sources}}
    ]}).forEach(function(discussion) {
        if (discussion.user in sources) {
            discussion.user = target._id;
        }
        discussion.discussion.forEach(message => {
            if (message.posted_by in sources) {
                message.posted_by = target._id;
            }
        });
        db.discussion.save(discussion);
        nb++;
    });
    return nb;
}

/**
 * Reaffect issues from sources to target
 * @param  {User} target  The target user receiving all the discussions
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected discussions
 */
function reaffectIssues(target, sources) {
    var nb = 0;
    db.issue.find({$or: [
        {user: {$in: sources}},
        {'discussion.posted_by': {$in: sources}}
    ]}).forEach(function(issue) {
        if (issue.user in sources) {
            issue.user = target._id;
        }
        issue.discussion.forEach(message => {
            if (message.posted_by in sources) {
                message.posted_by = target._id;
            }
        });
        db.issue.save(issue);
        nb++;
    });
    return nb;
}

/**
 * Reaffect activities from sources to target
 * @param  {User} target  The target user receiving all the activities
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected activities
 */
function reaffectActivities(target, sources) {
    var nb = 0;
    db.activities.find({$or: [
        {actor: {$in: sources}},
        {related_to: {$in: sources}}
    ]}).forEach(function(activity) {
        if (activity.actor in sources) {
            activity.actor = target._id;
        }
        if (activity.related_to in sources) {
            activity.related_to = target._id;
        }
        db.activity.save(activity);
        nb++;
    });
    return nb;
}

/**
 * Reaffect community resources from sources to target
 * @param  {User} target  The target user receiving all the community resources
 * @param  {Array} sources Array of user IDs soon to be deleted
 * @return {Integer}       Number of affected datasets
 */
function reaffectCommunityResource(target, sources) {
    return db.community_resource.update(
        {owner: {$in: sources}},
        {$set: {owner: target._id}},
        {multi: true}
    ).nModified;
}

/**
 * Affect  the sum of all metrics from sources to target
 * @param  {User} target  The target user receiving the aggregated metrics
 * @param  {Array} sources Array of users soon to be deleted
 */
function reaffectMetrics(target, sources) {
    const names = new Set(Object.keys(target.metrics));
    sources.forEach(function(source) {
        Object.keys(source.metrics).forEach(key => names.add(key));
    });
    for (var name in names.keys()) {
        target.matrics[name] = sources.reduce((previous, user) => {
            return previous + (user.metrics[name] || 0);
        }, target.matrics[name] || 0);
    }
    db.user.save(target);
    // return db.dataset.count({owner: {$in: sources}});
}


// Then group again to project all the duplicate emails as an array.
db.user.aggregate([
    // Group all the records having similar emails.
    {$group: {_id: '$email', ids: {$addToSet: '$_id'}, count: { $sum: 1 }}},
    // Match those groups having records greater than 1.
    {$match: {count: {$gt: 1}}},
]).forEach(function(row) {
    print(`Processing email ${row._id} (${row.count} duplicates)`);
    // Small volume, easier to manipulate arrays than cursors
    const users = db.user.find({email: row._id}).toArray().sort((u1, u2) => u1.created_at - u2.created_at);
    // Keep the first created user (will have the sorter slug without number)
    const kept = users[0];
    const to_delete = users.splice(1, users.length);
    const to_delete_ids = to_delete.map(user => user._id);

    const nbDatasets = reaffectDatasets(kept, to_delete_ids);
    if (nbDatasets) print(`Reaffected ${nbDatasets} datasets`);
    const nbMemberships = affectToOrganizations(kept, to_delete_ids);
    if (nbMemberships) print(`Affected to ${nbMemberships} organizations`);
    const nbReuses = reaffectReuses(kept, to_delete_ids);
    if (nbReuses) print(`Reaffected ${nbReuses} reuses`);
    const nbFollowers = reaffectFollowers(kept, to_delete_ids);
    if (nbFollowers) print(`Reaffected ${nbFollowers} followers`);
    const nbSubscriptions = reaffectSubsriptions(kept, to_delete_ids);
    if (nbSubscriptions) print(`Reaffected ${nbSubscriptions} subscriptions`);
    const nbDiscussions = reaffectDiscussions(kept, to_delete_ids);
    if (nbDiscussions) print(`Reaffected ${nbDiscussions} discussions`);
    const nbIssues = reaffectIssues(kept, to_delete_ids);
    if (nbIssues) print(`Reaffected ${nbIssues} issues`);
    const nbActivities = reaffectActivities(kept, to_delete_ids);
    if (nbActivities) print(`Reaffected ${nbActivities} activities`);
    const nbResources = reaffectCommunityResource(kept, to_delete_ids);
    if (nbResources) print(`Reaffected ${nbResources} community resources`);
    reaffectMetrics(kept, to_delete);

    // Delete remaining users
    const result = db.user.remove({_id: {$in: to_delete_ids}});
    print(`Deleted ${result.nRemoved} user(s)`);
});

print('Reindexation is required');
