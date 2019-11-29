import {List} from 'models/base';

class OrganizationRoles extends List {
    constructor(options) {
        super(options);
        this.$options.ns = 'organizations';
        this.$options.fetch = 'org_roles';
    }
};

const organization_roles = new OrganizationRoles().fetch();
export default organization_roles;