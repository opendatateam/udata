import {ModelPage} from 'models/base';

export default class ActivityPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'site';
        this.$options.fetch = 'activity';
    }
};
