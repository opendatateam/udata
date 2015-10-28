<template>
<vform v-ref="form" fields="{{fields}}" model="{{organization}}"></vform>
</template>

<script>
import Organization from 'models/organization';

export default {
    props: ['organization'],
    data: function() {
        return {
            organization: new Organization(),
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
                }]
        };
    },
    components: {
        'vform': require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            return this.$.form.serialize();
        },
        validate: function() {
            return this.$.form.validate();
        },
        on_error: function(response) {
            return this.$.form.on_error(response);
        },
    }
};
</script>
