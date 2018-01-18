/*
 * Ensure there's no duplicated members in each organization
 */

 function is_candidate() {
     return this.members && this.members.length > 1;
 }

 var uniqueMembers;
 var exist;
 var nbOrgs = 0;

 db.organization.find({'$where': is_candidate}).forEach(org => {
     uniqueMembers = [];
     org.members.forEach(member => {
         if (exist = uniqueMembers.find(m => m.user.equals(member.user))) {
             print(`Duplicate member ${member.user} for org ${org._id}`);
             // make sure the higher role is assigned to the deduped user
             if (member.role === 'admin') {
                 exist.role = 'admin'
             }
         } else {
             uniqueMembers.push(member);
         }
     })
     if (uniqueMembers.length !== org.members.length) {
         org.members = uniqueMembers;
         db.organization.save(org);
         nbOrgs++;
     }
 });

 print(`Deduplicated members of ${nbOrgs} organizations.`);
