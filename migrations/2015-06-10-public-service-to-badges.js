var organizations = db.organization.find({public_service: {$exists: true}});
var etalab = db.user.find({first_name: 'Etalab', last_name: 'Bot'})[0];
var counter = 0;

organizations.map(function(organization) {
    if (organization.public_service === true) {
        var ps_badge = {
            _cls: 'OrganizationBadge',
            kind: 'public-service',
            created: new Date(),
            created_by: etalab._id
        };
        var certified_badge = {
            _cls: 'OrganizationBadge',
            kind: 'certified',
            created: new Date(),
            created_by: etalab._id
        };
        var result = db.organization.update({_id: organization._id},
                               {$set: {badges: [ps_badge, certified_badge]}});
        counter += result.nModified;
    }
});
print(counter, 'organizations badged.');


var result = db.organization.update({public_service: {$exists: true}},
                       {$unset: {public_service: true}},
                       {multi: true});
print(result.nModified, 'organizations cleaned (removed public_service attribute).');
