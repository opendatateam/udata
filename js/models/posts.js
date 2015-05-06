define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Posts = ModelPage.extend({
        name: 'PostPage',
        ns: 'posts',
        fetch: 'list_posts'
    });

    return Posts;
});
