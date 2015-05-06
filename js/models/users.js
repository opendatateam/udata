define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Users = ModelPage.extend({
        name: 'UserPage',
        ns: 'users',
        fetch: 'list_users'
    });

    return Users;
});
