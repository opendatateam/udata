<style lang="less">

</style>

<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{reuse}}"></form-vertical>
</template>

<script>
'use strict';

var Reuse = require('models/reuse');

module.exports = {
    props: ['reuse'],
    data: function() {
        return {
            reuse: new Reuse(),
            fields: [{
                    id: 'title',
                    label: this._('Name')
                }, {
                    id: 'url',
                    label: this._('URL')
                }, {
                    id: 'type',
                    label: this._('Type'),
                    widget: 'select-input'
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'private',
                    label: this._('Private')
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
