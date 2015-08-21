import {List} from 'models/base';
import log from 'logger';


export default class GeoLevels extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'spatial';
        this.$options.fetch = 'spatial_levels';
    }
};
