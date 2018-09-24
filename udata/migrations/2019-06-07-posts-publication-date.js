/**
 * Fill publication date and delete the `private` attribute
 */

var updated = 0;

db.post.find().forEach(post => {
   if (!post.private) {
       post.published = post.created_at;
   }
   delete post.private;
   db.post.save(post);
   updated++;
});

print(`Updated ${updated} posts.`);
