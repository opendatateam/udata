import {List} from 'models/base';

export class AllowedExtensions extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'datasets';
        this.$options.fetch = 'allowed_extensions';
    }
}

export default new AllowedExtensions().fetch();
