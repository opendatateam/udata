define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var Post = Model.extend({
        name: 'Post',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.posts.get_post({post: ident}, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Post: no identifier specified');
                }
                return this;
            },
            save: function() {
                if (this.id) {
                    API.posts.update_post({
                        post: this.id,
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                } else {
                    API.posts.create_post({
                        payload: this.$data
                    },
                    this.on_fetched.bind(this));
                }
            }
        }
    });

    return Post;
});
