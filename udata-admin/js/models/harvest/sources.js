import {List} from 'models/base';
import log from 'logger';


export class HarvestSources extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'harvest';
        this.$options.fetch = 'list_harvest_sources';
    }
};

export var sources = new HarvestSources().fetch();
export default sources;
