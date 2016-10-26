<template>
<vform v-ref:form :fields="fields" :model="user"></vform>
</template>

<script>
import User from 'models/user';

export default {
    props: {
        user: {
            type: User,
            default: function() {return new User();}
        }
    },
    data: function() {
        return {
            fields: [{
                    id: 'first_name',
                    label: this._('First name')
                }, {
                    id: 'last_name',
                    label: this._('Last name'),
                }, {
                    id: 'about',
                    label: this._('About'),
                }, {
                    id: 'roles',
                    label: this._('Roles'),
                    widget: 'select-input',
                    values: [{id: 'admin', name: 'admin'}],
                    map: function(item) {
                        return {value: item.id, text: item.name};
                    },
                }]
        };
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
