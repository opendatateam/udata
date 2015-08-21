<template>
<form-vertical v-ref="form" fields="{{fields}}" model="{{reuse}}"></form-vertical>
</template>

<script>
import Reuse from 'models/reuse';
import reuse_types from 'models/reuse_types';

export default {
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
                    widget: 'select-input',
                    values: reuse_types.items.map(function(item) {
                        return {value: item.id, text: item.label};
                    })
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
