<template>
<vform v-ref:form :fields="fields" :model="user"></vform>
</template>

<script>
import User from 'models/user';

export default {
    props: {
        // Edited user
        user: {
            type: User,
            default: function() {return new User();}
        },
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
        if (this.$root.me.is_admin === true) {
            fields.push(
                {
                    id: 'roles',
                    label: this._('Roles'),
                    widget: 'select-input',
                    values: [{id: 'admin', name: 'admin'}],
                    map: function(item) {
                        return {value: item.id, text: item.name};
                    },
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
            return this.$refs.form.validate();
        },
        on_error: function(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
