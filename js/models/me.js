define(['api', 'models/user'], function(API, User) {
    'use strict';

    var me = new User({
        methods: {
            fetch: function() {
                API.me.get_me({}, this.on_fetched.bind(this));
                return this;
            }
        }
    });

    return me.fetch();
});
