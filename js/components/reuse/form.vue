<template>
<vform v-ref:form :fields="fields" :model="reuse"></vform>
</template>

<script>
import Reuse from 'models/reuse';
import reuse_types from 'models/reuse_types';

export default {
    props: {
        reuse: {
            type: Object,
            default: function() {
                return new Reuse();
            }
        }
    },
    data: function() {
        return {
            fields: [{
                    id: 'title',
                    label: this._('Name')
                }, {
                    id: 'url',
                    label: this._('URL'),
                    widget: 'url-field',
                }, {
                    id: 'type',
                    label: this._('Type'),
                    widget: 'select-input',
                    values: reuse_types,
                    map: function(item) {
                        return {value: item.id, text: item.label};
                    }
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
