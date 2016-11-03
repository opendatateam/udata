import {List} from 'models/base';
import log from 'logger';


export class Roles extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'users';
        this.$options.fetch = 'user_roles';
    }
};

export var roles = new Roles().fetch();
export default roles;
