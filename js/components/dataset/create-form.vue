<style lang="less">

</style>

<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{dataset}}"></form-vertical>
</template>

<script>
'use strict';

var Dataset = require('models/dataset');

module.exports = {
    props: ['dataset'],
    data: function() {
        return {
            dataset: new Dataset(),
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'license',
                    label: this._('License'),
                    widget: 'license-completer'
                }, {
                    id: 'frequency',
                    label: this._('Update frequency'),
                    widget: 'select-input'
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'temporal_coverage',
                    label: this._('Temporal coverage'),
                    widget: 'daterange-picker'
                }, {
                    id: 'spatial.zones',
                    label: this._('Spatial coverage'),
                    widget: 'zone-completer'
                }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            var data = this.$.form.serialize();
            data['spatial'] = {
                zones: data['spatial.zones'],
                // granularity: data['spatial.granularity']
            }
            delete data['spatial.zones'];
            // delete data['spatial.granularity'];
            return data;
        }
    }
};
</script>
