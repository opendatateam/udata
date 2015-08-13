<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{dataset}}"></form-vertical>
</template>

<script>
import Dataset from 'models/dataset';
import licenses from 'models/licenses';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';

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
                    widget: 'select-input',
                    values: licenses.items.map(function(item) {
                        return {value: item.id, text: item.title};
                    })
                }, {
                    id: 'frequency',
                    label: this._('Update frequency'),
                    widget: 'select-input',
                    values: frequencies.items.map(function(item) {
                        return {value: item.id, text: item.label};
                    })
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
                }, {
                    id: 'spatial.granularity',
                    label: this._('Spatial granularity'),
                    widget: 'select-input',
                    values: granularities.items.map(function(item) {
                        return {value: item.id, text: item.name};
                    })
                }, {
                    id: 'private',
                    label: this._('Private')
                }, {
                    id: 'organization',
                    widget: 'hidden-input',
                    type: 'hidden'
                }, {
                    id: 'owner',
                    widget: 'hidden-input',
                    type: 'hidden'
                }]
        };
    },
    components: {
        'form-vertical': require('components/form/vertical-form.vue')
    },
    methods: {
        serialize: function() {
            var data = this.$.form.serialize();
            console.log(data);
            // data['spatial'] = {
            //     zones: data['spatial.zones'],
            //     // granularity: data['spatial.granularity']
            // }
            // delete data['spatial.zones'];
            // delete data['spatial.granularity'];
            return data;
        },
        validate: function() {
            return this.$.form.validate();
        }
    }
};
</script>
