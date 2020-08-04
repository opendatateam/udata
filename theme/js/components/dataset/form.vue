<template>
<div>
<vertical-form v-ref:form :fields="fields" :model="dataset"></vertical-form>
</div>
</template>

<script>
import Dataset from 'models/dataset';
import licenses from 'models/licenses';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';
import VerticalForm from 'components/form/vertical-form.vue';

export default {
    components: {VerticalForm},
    props: {
        dataset: {
            type: Object,
            default: () => new Dataset(),
        },
    },
    data() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Title')
                }, {
                    id: 'acronym',
                    label: this._('Acronym')
                }, {
                    id: 'description',
                    label: this._('Description'),
                }, {
                    id: 'license',
                    label: this._('License'),
                    widget: 'select-input',
                    values: licenses,
                    map(item) {
                        return {value: item.id, text: item.title};
                    }
                }, {
                    id: 'frequency',
                    label: this._('Update frequency'),
                    widget: 'frequency-field',
                    frequency_date_id: 'frequency_date',
                    values: frequencies,
                    map(item) {
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
                    map(item) {
                        return {value: item.id, text: item.name};
                    }
                }, {
                    id: 'private',
                    label: this._('Private')
                }]
        };
    },

    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            return this.$refs.form.validate();
        },
        on_error(response) {
            return this.$refs.form.on_error(response);
        },
    }
};
</script>
