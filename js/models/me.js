define(['api', 'models/user', 'raven'], function(API, User, Raven) {
    'use strict';

    var me = new User({
        methods: {
            fetch: function() {
                API.me.get_me({}, this.on_user_fetched.bind(this));
                return this;
            },
            on_user_fetched: function(response) {
                Raven.setUserContext({
                    id: response.obj.id,
                    email: response.obj.email,
                    slug: response.obj.slug,
                    fullname: [response.obj.first_name, response.obj.last_name].join(' '),
                    is_authenticated: true,
                    is_anonymous: false
                });
                this.on_fetched(response);
            }
        }
    });

    return me.fetch();
});
