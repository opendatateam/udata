/**
 * Delete all activities of type `Activity.UserUpdatedDataset`
 */

var res = db.activity.deleteMany({_cls: "Activity.UserUpdatedDataset"});

print(`${res.deletedCount} activities removed.`);
