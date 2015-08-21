import {List} from 'models/base';
import log from 'logger';


export default class Requests extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'organizations';
        this.$options.fetch = 'list_membership_requests';
    }
};
