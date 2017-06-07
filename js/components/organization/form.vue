<template>
<vform v-ref:form :fields="fields" :model="organization"></vform>
</template>

<script>
import Organization from 'models/organization';

export default {
    props: {
        organization: {
            type: Object,
            default: function() {
                return new Organization();
            }
        },
        hideNotifications: false
    },
    data: function() {
        return {
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'acronym',
                    label: this._('Acronym')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'url',
                    label: this._('Website'),
                    widget: 'url-field',
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
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('Your organization has been updated.')
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
