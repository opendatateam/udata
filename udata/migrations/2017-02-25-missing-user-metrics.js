/*
 * Set default metric values on users
 */

const DEFAULT_METRICS = {
    'datasets': 0,
    'reuses': 0,
    'following': 0,
    'followers': 0,
};

var count = 0;
const users = db.user.find({$or: [
    {'metrics.datasets': {$exists: false}},
    {'metrics.reuses': {$exists: false}},
    {'metrics.following': {$exists: false}},
    {'metrics.followers': {$exists: false}},
]});

users.forEach(function(user) {
    user.metrics = Object.assign({}, DEFAULT_METRICS, users.metrics || {});
    db.user.save(user);
    count++;
});

print(`Updated ${count} user(s) missing metrics`);
