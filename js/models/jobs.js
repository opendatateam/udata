define(['api', 'models/base_list'], function(API, ModelList) {
    'use strict';

    var Jobs = ModelList.extend({
        name: 'Jobs',
        created: function() {
            this.fetch();
        },
        methods: {
            fetch: function() {
                API.workers.list_jobs({}, this.on_fetched.bind(this));
            }
        }
    });

    return new Jobs();
});
