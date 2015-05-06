define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Followers = ModelPage.extend({
        name: 'FollowPage',
        fetch: 'list_followers'
    });

    return Followers;
});
