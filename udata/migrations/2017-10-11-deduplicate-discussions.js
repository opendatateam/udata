/*
 * Deduplicate discussions by content, subject and author.
 */

var nbTopLevelRemoved = 0;
var nbNestedRemoved = 0;

function getUniqueAnswers(answers) {
    var uniqueAnswers = [];
    answers.forEach(answer => {
        const existing = uniqueAnswers.find(uAnswer => {
            return answer.posted_by.toString() === uAnswer.posted_by.toString()
                && answer.content === uAnswer.content;
        });
        if (!existing) uniqueAnswers.push(answer);
    });
    return uniqueAnswers;
}

// Remove duplicate top level discussions
// And re-assign non duplicated answers if any
db.discussion.aggregate([
    {$group: {
        _id: {author: '$user', subject: '$subject', title: '$title'},
        ids: {$addToSet: '$_id'},
        count: {$sum: 1}
    }},
    {$match: {count: {$gt: 1}}},
]).forEach(row => {
    const discussions = db.discussion.find({_id: {$in: row.ids}});
    const answers = discussions.toArray().reduce((acc, disc) => {
        return acc.concat(disc.discussion);
    }, []);
    var uniqueAnswers = getUniqueAnswers(answers);
    discussions[0].discussion = uniqueAnswers;
    db.discussion.save(discussions[0]);
    discussions.toArray().slice(1).forEach(discussion => {
        nbTopLevelRemoved += 1;
        db.discussion.remove({_id: discussion._id});
    });
});

print(`${nbTopLevelRemoved} top level discussion(s) removed.`);

// Remove duplicate nested comments
db.discussion.aggregate([
    {$unwind: '$discussion'},
    {$group: {
        _id: {author: '$user', subject: '$subject', title: '$title', content: '$discussion.content'},
        ids: {$addToSet: '$_id'},
        count: {$sum: 1}
    }},
    {$match: {count: {$gt: 1}}},
]).forEach(row => {
    discussion = db.discussion.find({_id: row.ids[0]})[0];
    const uniqueAnswers = getUniqueAnswers(discussion.discussion);
    nbNestedRemoved += (discussion.discussion.length - uniqueAnswers.length);
    discussion.discussion = uniqueAnswers;
    db.discussion.save(discussion);
});

print(`${nbNestedRemoved} nested level discussion(s) removed.`);
