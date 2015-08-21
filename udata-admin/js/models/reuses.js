import {ModelPage} from 'models/base';
import log from 'logger';


export default class ReusePage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'reuses';
        this.$options.fetch = 'list_reuses';
    }
};
