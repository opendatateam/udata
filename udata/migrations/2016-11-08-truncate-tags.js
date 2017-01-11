/*
 * Ensure all tags have a correct length
 *
 */

const MIN_TAG_LENGTH = 3
const MAX_TAG_LENGTH = 32

function migrate(collection) {

    var objects = collection.find({tags: {$gt: []}})
    var name = collection.getName()

    print(name + ' candidates : ' + objects.count());

    var objectsCounter = 0;
    var tagsCounter = 0;

    objects.forEach(function(object) {
        var tags = object.tags.map(function(tag) {
            if (tag.length > MAX_TAG_LENGTH)  {
                tagsCounter++;
                return tag.substring(0, MAX_TAG_LENGTH)
            }
            if (tag.length < MIN_TAG_LENGTH)  {
                tagsCounter++;
                return null
            }
            return tag;
        });
        tags = tags.filter(function(tag) { return tag !== null })
        var result = collection.update({_id: object._id},
                                       {$set: {tags: tags}});
        objectsCounter += result.nModified;
    });

    print(tagsCounter, name + ' tags modified.');
    print(objectsCounter, name + ' modified.');
}

migrate(db.dataset);
migrate(db.reuse);
