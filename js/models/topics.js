define(['api', 'models/base_page'], function(API, ModelPage) {
    'use strict';

    var Topics = ModelPage.extend({
        name: 'TopicPage',
        ns: 'topics',
        fetch: 'list_topics'
    });

    return Topics;
});
