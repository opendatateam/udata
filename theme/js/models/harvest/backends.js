import {List} from 'models/base';

export class HarvestBackends extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'harvest';
        this.$options.fetch = 'harvest_backends';
    }
}

export const harvest_backends = new HarvestBackends().fetch();
export default harvest_backends;
