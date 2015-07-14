import {List} from 'models/base';
import log from 'logger';


export class Jobs extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'workers';
        this.$options.fetch = 'lis_jobs';
    }
};

export var jobs = new Jobs().fetch();
export default jobs;
