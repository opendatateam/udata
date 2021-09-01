/*
 * Ensure active users have a confirmed_at date set.
 */

const result = db.user.update(
    {active: true, confirmed_at: null},
    {$set: {confirmed_at: new Date()}},
    {multi: true}
);
print(`${result.nModified} users migrated.`);
