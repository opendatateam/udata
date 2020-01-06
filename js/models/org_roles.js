import {List} from 'models/base';

class OrganizationRoles extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'organizations';
        this.$options.fetch = 'org_roles';
    }
};

const organizationRoles = new OrganizationRoles().fetch();
export default organizationRoles;