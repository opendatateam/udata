var sources = db.harvest_source.find({validated: {$exists: true}}),
    counter = 0;

sources.forEach(function(source) {
    source.validation = {
        state: source.validated ? 'accepted' : 'pending',
        comment: source.validation_comment,
        on: source.created_at
    };
    delete source.validated;
    db.harvest_source.save(source);
    counter++;
});

print(counter, 'sources modified.');
