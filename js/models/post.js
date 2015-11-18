import {Model} from 'models/base';
import log from 'logger';


export default class Post extends Model {
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('posts.get_post', {post: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Post: no identifier specified');
        }
        return this;
    }

    update(data, on_success, on_error) {
        this.$api('posts.update_post', {
            post: this.id,
            payload: data
        }, on_success, on_error);
    }

    save() {
        let data = {payload: this},
            endpoint = 'posts.create_post';

        if (this.id) {
            endpoint = 'posts.update_post';
            data.post = this.id;
        }
        this.$api(endpoint, data, this.on_fetched);
    }
};
