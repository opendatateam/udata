/*
 * Remove all topics datasets references that were deleted from the dataset
 * collection.
 */

function cleanTopics() {
  var count = 0;

  db.topic.find().forEach(function(topic) {
    topic.datasets.forEach(function(dataset) {
      if (!db.dataset.findOne(dataset)) {
        db.topic.update(topic, { $pull: { datasets: dataset } }, false, true);
        ++count;
      }
    });
  });

  return count;
}

var topicsCount = cleanTopics();
print('cleaned ' + topicsCount + ' datasets');
