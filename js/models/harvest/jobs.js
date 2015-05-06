define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var HarvestJobs = ModelPage.extend({
        name: 'HarvestJobPage',
        ns: 'harvest',
        fetch: 'list_harvest_jobs'
    });

    return HarvestJobs;
});
