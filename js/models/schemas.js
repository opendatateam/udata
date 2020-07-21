import {List} from 'models/base';


export class Schemas extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'schemas';
        this.sorted = 'label';
    }
}

export var schemas = new Schemas().fetch();
export default schemas;
