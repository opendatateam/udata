define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Issues = ModelPage.extend({
        name: 'IssuePage',
        ns: 'issues',
        fetch: 'list_issues'
    });

    return Issues;
});
