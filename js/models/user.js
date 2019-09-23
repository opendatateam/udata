import log from 'logger';
import {Model} from 'models/base';

export default class User extends Model {

    /**
     * The full name aka. concatenation between first_name and last_name.
     * @return {String}
     */
    get fullname() {
        return `${this.first_name} ${this.last_name}`;
    }

    /**
     * Is the user a site administrator.
     * @return {Boolean}
     */
    get is_admin() {
        return this.has_role('admin');
    }

    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.loading = true;
            this.$api('users.get_user', {user: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch User: no identifier specified');
        }
        return this;
    }

    update(data, on_error) {
        this.loading = true;
        this.$api('users.update_user', {
            user: this.id,
            payload: JSON.stringify(data)
        }, this.on_fetched, this.on_error(on_error));
    }

    /**
     * Check if the user has a given role
     * @param  {String}  name The role name
     * @return {Boolean}      True if the user has the role
     */
    has_role(name) {
        return this.roles && this.roles.indexOf(name) >= 0;
    }

    /**
     * Check if the user can edit a given object.
     * @param  {Object} object An object with owner and/or organization attributes
     * @return {Boolean}       True if can edit.
     */
    can_edit(object) {
        if (object === undefined) {
            return false;
        } else if (this.is_admin) {
            return true;
        } else if (object.owner) {
            return object.owner.id === this.id;
        } else if (object.organization) {
            return this.organizations.some(function(organization) {
                return organization.id === object.organization.id;
            });
        }
        return false;
    }
}
