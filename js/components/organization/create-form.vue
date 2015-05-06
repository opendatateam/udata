<style lang="less">

</style>

<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{organization}}"></form-vertical>
</template>

<script>
'use strict';

var Organization = require('models/organization');

module.exports = {
    paramAttributes: ['organization'],
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
        'form-vertical': require('components/form/vertical-form.vue')
    }
};
</script>
