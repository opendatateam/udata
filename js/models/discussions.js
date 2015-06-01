define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Discussions = ModelPage.extend({
        name: 'DiscussionPage',
        ns: 'discussions',
        fetch: 'list_discussions'
    });

    return Discussions;
});
