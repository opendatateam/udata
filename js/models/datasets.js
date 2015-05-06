define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Datasets = ModelPage.extend({
        name: 'DatasetPage',
        ns: 'datasets',
        fetch: 'list_datasets'
    });

    return Datasets;
});
