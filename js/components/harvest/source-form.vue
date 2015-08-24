<style lang="less">

</style>

<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{source}}"></form-vertical>
</template>

<script>
import HarvestSource from 'models/harvest/source';

module.exports = {
    props: ['source'],
    data: function() {
        return {
            source: new HarvestSource(),
            fields: [{
                id: 'name',
                label: this._('Name')
            }, {
                id: 'backend',
                label: this._('Backend')
            }, {
                id: 'url',
                label: this._('URL')
            }, {
                id: 'description',
                label: this._('Description'),
            }, {
                id: 'active',
                label: this._('Active')
            }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            return this.$.form.serialize();
        },
        validate: function() {
            return this.$.form.validate();
        }
    }
};
</script>
