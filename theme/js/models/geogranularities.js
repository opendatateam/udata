import {List} from 'models/base';


export class GeoGranularity extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'spatial';
        this.$options.fetch = 'spatial_granularities';
    }
}

export const granularities = new GeoGranularity().fetch();
export default granularities;
