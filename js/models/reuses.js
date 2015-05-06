define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Reuses = ModelPage.extend({
        name: 'ReusePage',
        ns: 'reuses',
        fetch: 'list_reuses'
    });

    return Reuses;
});
