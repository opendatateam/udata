import {Model} from 'models/base';
import log from 'logger';


export default class Organization extends Model {
    /**
     * Fetch an organization given its identifier, either an ID or a slug.
     * @param  {String} ident The organization identifier to fetch.
     * @return {Dataset}      The current object itself.
     */
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('organizations.get_organization', {org: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Organization: no identifier specified');
        }
        return this;
    }

    update(data, on_success, on_error) {
        this.$api('organizations.update_organization', {
            org: this.id,
            payload: JSON.stringify(data)
        }, on_success, on_error);
    }

    save() {
        let endpoint = this.id ? 'organizations.update_organization' : 'organizations.create_organization';
        this.$api(endpoint, {payload: this}, this.on_fetched);
    }

    create() {
        this.$api('organizations.create_organization', {
            payload: JSON.stringify(this.$data)
        }, this.on_fetched);
    }

    role_for(obj) {
        var user_id = obj.hasOwnProperty('id') ? obj.id : obj,
            members = this.members.filter(function(member) {
                return member.user.id === user_id;
            });
        return members.length ? members[0] : null;
    }

    is_member(obj) {
        return this.role_for(obj) != null;
    }

    is_admin(obj) {
        if (obj.is_admin) return true;
        var member = this.role_for(obj);
        return member != null ? member.role === 'admin' : false;
    }

    accept_membership(request, callback) {
        this.$api('organizations.accept_membership', {
            org: this.id,
            id: request.id
        }, function(response) {
            callback(response.obj);
        });
    }

    refuse_membership(request, comment, callback) {
        this.$api('organizations.refuse_membership', {
            org: this.id,
            id: request.id,
            payload: {comment: comment}
        }, function(response) {
            callback(response);
        });
    }
};

Organization.__badges_type__ =  'organization';
Organization.__key__ =  'org';
