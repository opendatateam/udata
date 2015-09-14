// Rename the dataconnexions badges to dataconnexions 5
var result = db.reuse.update(
    {'badges.kind': 'dataconnexions-candidate'},
    {$set: {'badges.$.kind': 'dataconnexions-5-candidate'}},
    {multi: true}
);
print(result.nModified, 'dataconnexions-candidate badges renamed.');

result = db.reuse.update(
    {'badges.kind': 'dataconnexions-laureate'},
    {$set: {'badges.$.kind': 'dataconnexions-5-laureate'}},
    {multi: true}
);
print(result.nModified, 'dataconnexions-laureate badges renamed.');
