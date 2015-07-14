import {List} from 'models/base';
import log from 'logger';


export class GeoLevels extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'spatial';
        this.$options.fetch = 'spatial_levels';
    }
};

export var levels = new GeoLevels().fetch();
export default levels;
