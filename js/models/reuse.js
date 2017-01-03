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
        let ep, args;
        if (this.id) {
            ep = 'reuses.update_reuse';
            args = {payload: this, reuse: this.id,};
        }
        else {
            ep = 'reuses.create_reuse';
            args = {payload: this,};
        }
        this.$api(ep, args, this.on_fetched, on_error);
    }

    update(data, on_success, on_error) {
        this.$api('reuses.update_reuse', {
            reuse: this.id,
            payload: data
        }, on_success, on_error);
    }
};

Reuse.__badges_type__ = 'reuse';
