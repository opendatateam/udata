var issues = db.issue.find();

issues.map(function(issue) {
    var title = issue.discussion[0].content;
    title = title.trim().replace('Bonjour,', '').trim();
    title = title.split('\n')[0].trim();
    title = title.split('.')[0];
    issue.title = title;
    if (issue.type === 'illegal' || issue.type === 'advertisement') {
        issue.type = 'tendencious';
    }
    db.issue.save(issue);
});
