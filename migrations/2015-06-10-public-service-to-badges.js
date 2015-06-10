var organizations = db.organization.find();
var etalab = db.user.find({first_name: 'Etalab', last_name: 'Bot'})[0];

organizations.map(function(organization) {
    if (organization.public_service === true) {
        // Create two badges from the previous boolean field.
        db.badge.save({
            _cls: 'Badge.OrganizationBadge',
            subject: organization._id,
            kind: 'public-service',
            created: new Date(),
            created_by: etalab._id
        });
        db.badge.save({
            _cls: 'Badge.OrganizationBadge',
            subject: organization._id,
            kind: 'certified',
            created: new Date(),
            created_by: etalab._id
        });
    }
    // Delete the now useless boolean field.
    db.organization.update({_id: organization._id},
                           {$unset: {public_service: true}});
});
