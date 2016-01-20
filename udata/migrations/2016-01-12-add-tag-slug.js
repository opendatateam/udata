/*
 * Add the slug property to Tags with a default value based on the name
 * property.
 */

// Taken from underscore.string
function slugify(str) {
  var from = 'ąàáäâãåæăćęèéëêìíïîłńòóöôõøśșțùúüûñçżź';
  var to = 'aaaaaaaaaceeeeeiiiilnoooooosstuuuunczz';
  var converted = '[%s]'.replace('%s',
    from.replace(/([.*+?^=!:${}()|[\]\/\\])/g, '\\$1'));
  var regex = new RegExp(converted, 'g');

  str = String(str).toLowerCase().replace(regex, function(c) {
    var index = from.indexOf(c);
    return to.charAt(index) || '-';
  });

  str = str.replace(/[^\w\s-]/g, '');
  str = str.trim();
  str = str.replace(/([A-Z])/g, '-$1');
  str = str.replace(/[-_\s]+/g, '-');
  str = str.toLowerCase();
  return str;
}

function convertTags(table) {
  var records = db[table].find();
  var count = 0;

  records.forEach(function(record) {
    var tags = [];
    var recordTags = record.tags;
    var tag;
    for(i in recordTags) {
      tag = recordTags[i];
      tag = slugify(tag);
      if(tags.indexOf(tag) == -1) {
        tags.push(tag);
      }
    }
    record.tags = tags;
    db[table].save(record);
    ++count;
  });
  return count;
}

var datasetsCount = convertTags('dataset');
print('Migrated tags for ' + datasetsCount + ' datasets');

var reusesCount = convertTags('reuse');
print('Migrated tags for ' + reusesCount + ' reuses');
