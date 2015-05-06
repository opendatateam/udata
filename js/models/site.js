define(['api', 'models/base'], function(API, Model) {
    'use strict';

    var Site = Model.extend({
        name: 'Site',
        methods: {
            fetch: function() {
                API.site.get_site({}, this.on_fetched.bind(this));
                return this;
            }
        }
    });

    return new Site().fetch();
});
