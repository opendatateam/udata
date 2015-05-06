define(['api', 'models/base', 'jquery', 'logger'], function(API, Model, $, log) {
    'use strict';

    var Topic = Model.extend({
        name: 'Topic',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.topics.get_topic({topic: ident}, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Topic: no identifier specified');
                }
                return this;
            },
            save: function() {
                if (this.id) {
                    API.topics.update_topic({
                        topic: this.id,
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                } else {
                    API.topics.create_topic({
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                }
            }
        }
    });

    return Topic;
});
