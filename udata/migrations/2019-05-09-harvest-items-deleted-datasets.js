/**
 * Delete references to deleted datasets
 */

var updated = 0;
var nbDays = config.HARVEST_JOBS_RETENTION_DAYS;
var minDate = new Date(ISODate().getTime() - 1000 * 60 * 60 * 24 * nbDays);

// Delete jobs older then minDate
var result = db.harvest_job.deleteMany({'created': {'$lt': minDate}});
print(`Deleted ${result.deletedCount} HarvestJobs according to retention policy (${config.HARVEST_JOBS_RETENTION_DAYS} days)`);

// Match all HarvestJob.items.dataset not found in dataset collection
const pipeline = [
    {$unwind: '$items'},  // One row by item
    {$group: {_id: null, datasetId: {$addToSet: '$items.dataset'}}}, // Distinct Dataset IDs
    {$unwind: '$datasetId'}, // One row by ID
    {$lookup: {from: 'dataset', localField: 'datasetId', foreignField: '_id', as: 'dataset'}}, // Join
    {$match: {'dataset': [] }} // Only keep IDs without match
];

const index = {'items.dataset': 1};

db.harvest_job.createIndex(index);
db.harvest_job.aggregate(pipeline).forEach(row => {
    const result = db.harvest_job.update(
        {'items.dataset': row.datasetId},
        {'$set': {'items.$.dataset': null}},
        {multi: true}
    );
    updated += result.nModified;
});
db.harvest_job.dropIndex(index);

print(`Updated ${updated} HarvestJob.items.dataset broken references.`);
