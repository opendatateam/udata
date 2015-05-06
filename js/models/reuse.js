define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var Reuse = Model.extend({
        name: 'Reuse',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.reuses.get_reuse({reuse: ident}, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Reuse: no identifier specified');
                }
                return this;
            },
            save: function() {
                if (this.id) {
                    API.reuses.update_reuse({
                        reuse: this.id,
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                } else {
                    API.reuses.create_reuse({
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                }
            }
        }
    });

    return Reuse;
});
