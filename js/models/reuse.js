import {Model} from 'models/base';
import log from 'logger';


export default class Reuse extends Model {
    /**
     * Fetch a reuse given its identifier, either an ID or a slug.
     * @param  {String} ident The reuse identifier to fetch.
     * @return {Dataset}      The current object itself.
     */
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('reuses.get_reuse', {reuse: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Reuse: no identifier specified');
        }
        return this;
    }

    /**
     * Create or update the given reuse
     */
    save(on_error) {
        if (this.id) {
            return this.update(this, on_error);
        }
        this.$api('reuses.create_reuse', {payload: this}, this.on_fetched, on_error);
    }

    update(data, on_error) {
        this.$api('reuses.update_reuse', {
            reuse: this.id,
            payload: data
        }, this.on_fetched, on_error);
    }
}

Reuse.__badges_type__ = 'reuse';
