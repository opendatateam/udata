<template>
<div>
    <v-form v-ref:form :fields="fields" :model="user"></v-form>
</div>
</template>

<script>
import roles from 'models/roles';
import User from 'models/user';
import VForm from 'components/form/vertical-form.vue';

export default {
    components: {VForm},
    props: {
        // Edited user
        user: {
            type: User,
            default: () => new User(),
        }
    },
    data() {
        const fields = [
            {
                id: 'first_name',
                label: this._('First name'),
            },
            {
                id: 'last_name',
                label: this._('Last name'),
            },
            {
                id: 'website',
                label: this._('Website'),
            },
            {
                id: 'about',
                label: this._('About'),
            },
        ]
        if (this.$root.me.is_admin) {
            fields.push(
                {
                    id: 'roles',
                    label: this._('Roles'),
                    widget: 'select-input',
                    multiple: true,
                    values: roles,
                    map: item => {return {value: item.name, text: item.name}},
                },
                {
                    id: 'active',
                    label: this._('Active'),
                    widget: 'checkbox',
                }
            )
        }
        return {fields};
    },
    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            return this.$refs.form.validate();
        },
        on_error(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
