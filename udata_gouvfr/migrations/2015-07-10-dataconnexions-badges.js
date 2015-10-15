var reuses = db.reuse.find({tags: 'dataconnexions'});
var etalab = db.user.find({first_name: 'Etalab', last_name: 'Bot'})[0];
var counter = 0;

reuses.map(function(reuse) {
    var dataconnexions_badge = {
        _cls: 'ReuseBadge',
        kind: 'dataconnexions-candidate',
        created: new Date(),
        created_by: etalab._id
    };
    var result = db.reuse.update({_id: reuse._id},
                                 {$set: {badges: [dataconnexions_badge]}});
    counter += result.nModified;
});
print(counter, 'reuses badged.');

var result = db.reuse.update({tags: 'dataconnexions'},
                             {$pull: {tags: 'dataconnexions'}},
                             {multi: true});
print(result.nModified, 'reuses cleaned (removed dataconnexions tag).');
