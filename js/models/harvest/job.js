import {Model} from 'models/base';
import log from 'logger';


export default class HarvestJob extends Model {
    fetch() {
        if (this.id || this.slug) {
            this.$api('harvest.get_job', {
                dataset: this.id || this.slug
            }, this.on_fetched);
        } else {
            log.error('Unable to fetch Dataset: no identifier specified');
        }
        return this;
    }
};
