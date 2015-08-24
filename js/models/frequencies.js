import {List} from 'models/base';
import log from 'logger';


export class Frequencies extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'list_frequencies';
    }
};

export var frequencies = new Frequencies().fetch();
export default frequencies;
