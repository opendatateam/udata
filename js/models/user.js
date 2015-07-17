import log from 'logger';
import {Model} from 'models/base';

export default class User extends Model {

    get fullname() {
        return this.first_name + ' ' + this.last_name;
    }

    get is_admin() {
        return this.has_role('admin');
    }

    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('users.get_user', {user: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch User: no identifier specified');
        }
        return this;
    }

    has_role(name) {
        return this.roles && this.roles.indexOf(name) >= 0;
    }
};
