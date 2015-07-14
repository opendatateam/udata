import {Model} from 'models/base';
import log from 'logger';


export default class HarvestSource extends Model {
    fetch(ident) {
        ident = ident || this.id || this.slug;
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
};
