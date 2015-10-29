<template>
<form-vertical v-ref:form fields="{{fields}}" model="{{user}}"></form-vertical>
</template>

<script>
'use strict';

var User = require('models/user');

module.exports = {
    props: ['user'],
    data: function() {
        return {
            user: new User(),
            fields: [{
                    id: 'first_name',
                    label: this._('First name')
                }, {
                    id: 'last_name',
                    label: this._('Last name'),
                }, {
                    id: 'about',
                    label: this._('About'),
                }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
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
