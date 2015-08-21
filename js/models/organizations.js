import {ModelPage} from 'models/base';
import log from 'logger';


export default class OrganizationPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'organizations';
        this.$options.fetch = 'list_organizations';
    }
};
