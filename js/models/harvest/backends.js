import {List} from 'models/base';
import log from 'logger';


export class HarvestBackends extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'harvest';
        this.$options.fetch = 'harvest_backends';
    }
};

export var harvest_backends = new HarvestBackends().fetch();
export default harvest_backends;
