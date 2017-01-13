import {Model} from 'models/base';
import log from 'logger';


export default class HarvestSource extends Model {
    fetch(ident) {
        ident = ident || this.id || this.slug;
        this.loading = true;
        if (ident) {
            this.$api('harvest.get_harvest_source',
                {ident: ident},
                this.on_fetched
            );
        } else {
            log.error('Unable to fetch HarvestSource: no identifier specified');
        }
        return this;
    }

    /**
     * Create or update the given harvest source.
     */
    save() {
        const ep = this.id ? 'harvest.update_harvest_source' : 'harvest.create_harvest_source';
        this.loading = true;
        this.$api(ep, {payload: this}, this.on_fetched);
    }

    update(data, on_success, on_error) {
        this.loading = true;
        this.$api('harvest.update_harvest_source', {
            ident: this.id,
            payload: data
        }, on_success, on_error);
    }
}
