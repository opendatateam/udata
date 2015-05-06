define(['api', 'models/base_list', 'jquery'], function(API, BaseList, $) {
    'use strict';

    var Requests = BaseList.extend({
        name: 'Requests',
        ns: 'organizations',
        fetch: 'list_membership_requests'
    });

    return Requests;

});
