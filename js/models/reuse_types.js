import {List} from 'models/base';
import log from 'logger';


export class ReuseTypes extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'reuses';
        this.$options.fetch = 'reuse_types';
    }
};

export var reuse_types = new ReuseTypes().fetch();
export default reuse_types;
