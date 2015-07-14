import {ModelPage} from 'models/base';
import log from 'logger';


export default class UserPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'users';
        this.$options.fetch = 'list_users';
    }
};
