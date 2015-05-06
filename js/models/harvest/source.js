define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var HarvestSource = Model.extend({
        name: 'HarvestSource',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.harvest.get_harvest_source(
                        {ident: ident},
                        this.on_fetched.bind(this)
                    );
                } else {
                    log.error('Unable to fetch HarvestSource: no identifier specified');
                }
                return this;
            }
        }
    });

    return HarvestSource;
});
