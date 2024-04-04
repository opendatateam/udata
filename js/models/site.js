import {Model} from 'models/base';
import log from 'logger';


export class Site extends Model {
    fetch() {
        this.loading = true;
        this.$api('site.get_site', {}, this.on_fetched);
        return this;
    }
};

export var site = new Site().fetch();
export default site;
