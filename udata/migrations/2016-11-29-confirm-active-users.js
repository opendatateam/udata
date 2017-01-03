/*
 * As email confirmation is required to be active
 * this migration confirm all active users.
 */

var result = db.user.update(
    {active: true, confirmed_at: {$exists: false}},
    {$set: {confirmed_at: new Date()}}, // Use current date as effective confirmation happens now
    {multi: true}
);

print(`Updated ${result.nModified} users`);
