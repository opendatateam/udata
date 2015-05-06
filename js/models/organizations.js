define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Organizations = ModelPage.extend({
        name: 'OrganizationPage',
        ns: 'organizations',
        fetch: 'list_organizations'
    });

    return Organizations;
});
