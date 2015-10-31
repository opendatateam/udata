<template>
<vform v-ref:form :fields="fields" :model="dataset"></vform>
</template>

<script>
import Dataset from 'models/dataset';
import licenses from 'models/licenses';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';

export default {
    props: {
        dataset: {
            type: Object,
            default: function() {
                return new Dataset();
            }
        }
    },
    data: function() {
        return {
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
                    values: licenses,
                    map: function(item) {
                        return {value: item.id, text: item.title};
                    }
                }, {
                    id: 'frequency',
                    label: this._('Update frequency'),
                    widget: 'frequency-field',
                    frequency_date_id: 'frequency_date',
                    values: frequencies,
                    map: function(item) {
                        return {value: item.id, text: item.label};
                    }
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
                    values: granularities,
                    map: function(item) {
                        return {value: item.id, text: item.name};
                    }
                }, {
                    id: 'private',
                    label: this._('Private')
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
