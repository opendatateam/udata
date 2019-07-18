import {Model} from 'models/base';
import log from 'logger';


export default class Topic extends Model {
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('topics.get_topic', {topic: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Topic: no identifier specified');
        }
        return this;
    }

    save(on_error) {
        this.loading = true;
        if (this.id) {
            this.$api('topics.update_topic', {
                topic: this.id,
                payload: this
            },
            this.on_fetched, this.on_error(on_error));
        } else {
            this.$api('topics.create_topic', {
                payload: this
            },
            this.on_fetched, this.on_error(on_error));
        }
    }

    update(data, on_success, on_error) {
        this.loading = true;
        this.$api('topics.update_topic', {
            topic: this.id,
            payload: data
        }, on_success, this.on_error(on_error));
    }
}
