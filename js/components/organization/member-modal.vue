<style lang="less">
.member-form {
    .form-group {
        margin-bottom: 0;
    }
}

.user-modal {
    .btn-group-justified:not(:last-child) {
        margin-bottom: 5px;
    }
}
</style>

<template>
<div>
<user-modal :user="user" v-ref:modal>
    <role-form class="member-form" v-ref:form
        :fields="fields" :model="member"
        :readonly="!can_edit" :fill="true">
    </role-form>
    <br v-if="can_edit" />
    <div v-if="can_edit"  class="btn-group btn-group-justified">
        <div class="btn-group">
            <button type="button" class="btn btn-success btn-flat"
                @click="submit">
                <span class="fa fa-check"></span>
                {{ _('Validate') }}
            </button>
        </div>
        <div class="btn-group">
            <button type="button" class="btn btn-warning btn-flat" @click="$refs.modal.close">
                <span class="fa fa-close"></span>
                {{ _('Cancel') }}
            </button>
        </div>
    </div>
    <div v-if="can_edit && member_exists" class="btn-group btn-group-justified">
        <div class="btn-group">
            <button type="button" class="btn btn-danger btn-flat" @click="delete">
                <span class="fa fa-user-times"></span>
                {{ _('Delete') }}
            </button>
        </div>
    </div>
</user-modal>
</div>
</template>

<script>
import API from 'api';
import User from 'models/user';
import Organization from 'models/organization';
import organizationRoles from 'models/org_roles';
import UserModal from 'components/user/modal.vue';
import RoleForm from 'components/form/horizontal-form.vue';

export default {
    name: 'member-modal',
    components: {UserModal, RoleForm},
    props: {
        member: {
            type: Object,
            default() {return {};}
        },
        org: Organization
    },
    data() {
        return {
            user: new User(),
            fields: [{
                id: 'role',
                label: this._('Role'),
                widget: 'select-input',
                values: organizationRoles,
                map(item) {
                    return {value: item.id, text: item.label};
                }
            }]
        };
    },
    computed: {
        can_edit() {
            return this.org.is_admin(this.$root.me);
        },
        member_exists() {
            return this.org.is_member(this.user);
        }
    },
    ready() {
        this.user.fetch(this.member.user.id);
    },
    methods: {
        delete() {
            API.organizations.delete_organization_member(
                {org: this.org.id, user: this.user.id},
                this.on_deleted.bind(this),
                this.$root.handleApiError
            );
        },
        on_deleted(response) {
            this.org.fetch();
            this.$dispatch('notify', {
                title: this._('Member deleted'),
                details: this._('{user} is not a member of this organization anymore')
                    .replace('{user}', this.user.fullname)
            });
            this.$refs.modal.close();
        },
        submit() {
            const data = {
                org: this.org.id,
                user: this.user.id,
                payload: this.$refs.form.serialize()
            };
            if (this.member_exists) {
                API.organizations.update_organization_member(data, this.on_updated.bind(this), this.$root.handleApiError);
            } else {
                API.organizations.create_organization_member(data, this.on_created.bind(this), this.$root.handleApiError);
            }
        },
        on_created(response) {
            this.org.fetch();
            this.$dispatch('notify', {
                title: this._('Member added'),
                details: this._('{user} is now {role} of this organization')
                    .replace('{user}', this.user.fullname)
                    .replace('{role}', response.obj.role)
            });
            this.$refs.modal.close();
        },
        on_updated(response) {
            this.org.fetch();
            this.$dispatch('notify', {
                title: this._('Member role updated'),
                details: this._('{user} is now {role} of this organization')
                    .replace('{user}', this.user.fullname)
                    .replace('{role}', response.obj.role)
            });
            this.$refs.modal.close();
        }
    }
};
</script>
