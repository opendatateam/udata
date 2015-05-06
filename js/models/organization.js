define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var Organization = Model.extend({
        name: 'Organization',
        icon: 'building',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.organizations.get_organization({
                        org: ident
                    }, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Organization: no identifier specified');
                }
                return this;
            },
            update: function(data) {
                API.organizations.update_organization({
                    org: this.id,
                    payload: JSON.stringify(data)
                }, this.on_fetched.bind(this));
            },
            save: function() {
                var method = this.id ? API.organizations.update_organization : API.organizations.create_organization;
                method({payload: this.$data}, this.on_fetched.bind(this));
            },
            create: function() {
                API.organizations.create_organization({
                    payload: JSON.stringify(this.$data)
                }, this.on_fetched.bind(this));
            },
            role_for: function(obj) {
                var user_id = obj.hasOwnProperty('id') ? obj.id : obj,
                    members = this.members.filter(function(member) {
                        return member.user.id == user_id;
                    });
                return members.length ? members[0] : null;
            },
            is_member: function(obj) {
                return this.role_for(obj) != null;
            },
            is_admin: function(obj) {
                if (obj.is_admin) return true;
                var member = this.role_for(obj);
                return member != null ? member.role === 'admin' : false;
            },
            accept_membership: function(request, callback) {
                API.organizations.accept_membership({
                    org: this.id,
                    id: request.id
                }, function(response) {
                    callback(response.obj)
                });
            },
            refuse_membership: function(request, comment, callback) {
                API.organizations.refuse_membership({
                    org: this.id,
                    id: request.id,
                    payload: JSON.stringify({comment: comment})
                }, function(response) {
                    callback(response.obj)
                });
            }
        }
    });

    return Organization;
});
