<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{source}}"></form-vertical>
</template>

<script>
import HarvestSource from 'models/harvest/source';
import backends from 'models/harvest/backends';

export default {
    name: 'HarvestSourceForm',
    props: ['source'],
    data: function() {
        return {
            source: new HarvestSource(),
            fields: [{
                    id: 'name',
                    label: this._('Nom')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'url',
                    label: this._('URL'),
                }, {
                    id: 'backend',
                    label: this._('Backend'),
                    widget: 'select-input',
                    values: backends.items.map(function(item) {
                        return {value: item.id, text: item.label};
                    })
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
