import log from 'logger';
import {Model} from 'models/base';

export default class MyMetrics extends Model {

    fetch(id) {
        this.loading = true;
        this.$api('me.my_metrics', {id: id}, this.on_fetched);
        return this;
    }

}
