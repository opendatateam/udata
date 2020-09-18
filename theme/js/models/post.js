import {Model} from 'models/base';
import Dataset from 'models/dataset';
import Reuse from 'models/reuse';
import log from 'logger';


export default class Post extends Model {
    fetch(ident, mask) {
        ident = ident || this.id || this.slug;
        const options = {post: ident};
        if (mask) {
            options['X-Fields'] = mask;
        }
        if (ident) {
            this.loading = true;
            this.$api('posts.get_post', options, this.on_fetched);
        } else {
            log.error('Unable to fetch Post: no identifier specified');
        }
        return this;
    }

    on_fetched(data) {
        super.on_fetched(data);
        // Cast lists to benefit from helpers
        this.datasets = this.datasets.map(d => new Dataset({data: d}));
        this.reuses = this.reuses.map(r => new Reuse({data: r}));
    }

    update(data, on_success, on_error) {
        this.loading = true;
        this.$api('posts.update_post', {
            post: this.id,
            payload: data
        }, on_success, this.on_error(on_error));
    }

    save(on_error) {
        const data = {payload: this};
        let endpoint = 'posts.create_post';
        this.loading = true;

        if (this.id) {
            endpoint = 'posts.update_post';
            data.post = this.id;
        }
        this.$api(endpoint, data, this.on_fetched, this.on_error(on_error));
    }
};
