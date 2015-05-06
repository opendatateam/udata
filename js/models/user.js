define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var User = Model.extend({
        name: 'User',
        computed: {
            fullname: function() {
                return this.$data.fullname ? this.$data.fullname : this.first_name + ' ' + this.last_name;
            },
            is_admin: function() {
                return this.has_role('admin');
            }
        },
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.users.get_user({
                        user: ident
                    }, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch User: no identifier specified');
                }
                return this;
            },
            has_role: function(name) {
                return this.roles && this.roles.indexOf(name) >= 0;
            }
        }
    });

    return User;
});
