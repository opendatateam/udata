define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var HarvestJob = Model.extend({
        name: 'HarvestJob',
        methods: {
            fetch: function() {
                if (this.id || this.slug) {
                    API.harvest.get_job({
                        dataset: this.id || this.slug
                    }, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Dataset: no identifier specified');
                }
                return this;
            }
        }
    });

    return HarvestJob;
});
