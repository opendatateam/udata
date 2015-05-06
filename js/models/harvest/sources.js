define(['api', 'models/base_list'], function(API, ModelList) {
    'use strict';

    var HarvestSources = ModelList.extend({
        name: 'HarvestSources',
        created: function() {
            this.fetch();
        },
        methods: {
            fetch: function() {
                API.harvest.list_harvest_sources({}, this.on_fetched.bind(this));
            }
        }
    });

    return new HarvestSources();
});
