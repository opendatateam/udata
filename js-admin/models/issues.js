import {ModelPage} from 'models/base';
import log from 'logger';


export default class IssuePage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'issues';
        this.$options.fetch = 'list_issues';
    }
};
