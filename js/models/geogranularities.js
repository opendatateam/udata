import {List} from 'models/base';
import log from 'logger';


export default class GeoGranularity extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'spatial';
        this.$options.fetch = 'spatial_granularities';
    }
};

export var granularities = new GeoGranularity().fetch();
export default granularities;
