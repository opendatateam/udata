import {List} from 'models/base';

export class ResourceTypes extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'resource_types';
    }
};

export var reuse_types = new ResourceTypes().fetch();
export default reuse_types;
