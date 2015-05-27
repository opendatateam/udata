var issues = db.issue.find();

issues.map(function(issue) {
    var title = issue.discussion[0].content;
    title = title.trim().replace('Bonjour,', '').trim();
    title = title.split('\n')[0].trim();
    title = title.split('.')[0];
    if (issue.type === 'other') {
        var newCls = '';
        // Deal with Dataset vs. Reuse.
        if (issue._cls === 'Issue.DatasetIssue') {
            newCls = 'Discussion.DatasetDiscussion';
        } else if (issue._cls === 'Issue.ReuseIssue') {
            newCls = 'Discussion.ReuseDiscussion';
        }
        // Create a discussion from the previous issue
        // and delete the latter.
        db.discussion.save({
            _cls: newCls,
            user: issue.user,
            subject: issue.subject,
            title: title,
            discussion: issue.discussion,
            created: issue.created,
            closed: issue.closed,
            closed_by: issue.closed_by
        });
        db.issue.remove({_id: issue._id});
    } else {
        // Remove the now useless type and save the new title.
        db.issue.update({_id: issue._id},
                        {$set: {title: title}, $unset: {type: true}});
    }
});
