import {List} from 'models/base';
import log from 'logger';


export class Licenses extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'list_licenses';
    }
};

export var licenses = new Licenses().fetch();
export default licenses;
