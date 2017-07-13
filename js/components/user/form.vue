<template>
<div>
    <vform v-ref:form :fields="fields" :model="user"></vform>
</div>
</template>

<script>
import roles from 'models/roles';
import User from 'models/user';

export default {
    props: {
        // Edited user
        user: {
            type: User,
            default: function() {return new User();}
        },
        hideNotifications: false
    },
    data: function() {
        let fields = [
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
    components: {
        vform: require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            return this.$refs.form.serialize();
        },
        validate: function() {
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('Your profile has been updated.')
                });
            }
            return isValid;
        },
        on_error: function(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
