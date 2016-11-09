import {List} from 'models/base';

class Roles extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'users';
        this.$options.fetch = 'user_roles';
    }
};

const roles = new Roles().fetch();
export default roles;
